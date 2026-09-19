include $(APPDIR)/Make.defs

PROGNAME = qiji_chat qiji_config
PRIORITY = 100 100
STACKSIZE = 32768 32768
MODULE = $(CONFIG_GEMINI_CHAT_MINIMAL)
MAINSRC = gemini_chat_main.c qiji_config_main.c
CSRCS = qiji_network.c qiji_avatar.c qiji_aliyun_asr.c
CFLAGS += ${INCDIR_PREFIX}$(APPDIR)/packages/ai_agent/include
CFLAGS += ${INCDIR_PREFIX}$(APPDIR)/packages/ai_agent/src
CFLAGS += ${INCDIR_PREFIX}$(APPDIR)/netutils/cjson/cJSON
CFLAGS += ${INCDIR_PREFIX}$(APPDIR)/crypto/mbedtls/mbedtls/include

include $(APPDIR)/Application.mk
