#include "../../app/gemini_chat_minimal/qiji_audio_envelope.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    qiji_audio_envelope_t e, fragmented;
    uint8_t pcm[960 * 2];
    qiji_envelope_reset(&e);
    qiji_envelope_reset(&fragmented);
    memset(pcm, 0, sizeof(pcm));
    qiji_envelope_push(&e, pcm, sizeof(pcm));
    assert(qiji_envelope_at(&e, 0) == 0);
    /* INT16_MIN must not overflow signed 16-bit abs. */
    for (unsigned i = 0; i < sizeof(pcm); i += 2) { pcm[i] = 0; pcm[i+1] = 128; }
    qiji_envelope_push(&e, pcm, sizeof(pcm));
    assert(qiji_envelope_at(&e, 40) == 255);
    assert(qiji_envelope_at(&e, 80) == 0);
    qiji_envelope_reset(&e);
    for (unsigned i = 0; i < sizeof(pcm); i += 2) { pcm[i] = 232; pcm[i+1] = 3; }
    qiji_envelope_push(&e, pcm, sizeof(pcm));
    for (unsigned i = 0; i < sizeof(pcm); i++) qiji_envelope_push(&fragmented, pcm+i, 1);
    assert(!memcmp(&e, &fragmented, sizeof(e)));
    assert(qiji_envelope_at(&e, 0) > 18 && qiji_envelope_at(&e, 0) < 115);
    for (unsigned n = 0; n < QIJI_ENV_BINS; n++) qiji_envelope_push(&e, pcm, sizeof(pcm));
    assert(qiji_envelope_at(&e, 0) == 0); /* overwritten data cannot animate old speech */
    assert(qiji_envelope_at(&e, QIJI_ENV_BINS*40) > 0);
    qiji_envelope_reset(&e);
    assert(qiji_envelope_at(&e, 0) == 0 && e.windows == 0);
    qiji_envelope_push(&e, pcm, 22);
    assert(qiji_envelope_at(&e, 0) > 0); /* final partial window */
    puts("PASS: PCM silence, amplitude, signed limits, split samples, ring bounds and reset");
}
