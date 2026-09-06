/**
 * 设置抽屉
 * - 从底部滑出的玻璃面板
 * - LLM 模型、TTS 音色、语速、角色提示词
 */
import { clsx } from "clsx";
import { X, Sliders } from "lucide-react";
import { useState } from "react";
import { useAppStore } from "@/store/appStore";
import type { RuntimeConfig } from "@/types/chat";

interface SettingsDrawerProps {
  open: boolean;
  onClose: () => void;
  onUpdate: (partial: Partial<RuntimeConfig>) => void;
}

// 预设模型列表（官方控制台确认的 Model ID，用户也可手动输入其它 ID）
const LLM_MODELS = [
  { id: "doubao-seed-2-1-turbo-260628", label: "豆包 Seed 2.1 Turbo（轻量快速，推荐）" },
  { id: "doubao-seed-1-6-flash-250828", label: "豆包 Seed 1.6 Flash" },
  { id: "doubao-seed-1-6-251015", label: "豆包 Seed 1.6（最新版）" },
  { id: "doubao-seed-1-6-250615", label: "豆包 Seed 1.6" },
  { id: "doubao-seed-1-6-thinking-250715", label: "豆包 Seed 1.6 Thinking（深度思考）" },
  { id: "deepseek-v3-1-250821", label: "DeepSeek V3.1" },
  { id: "doubao-1-5-pro-32k-250115", label: "豆包 1.5 Pro" },
];

const TTS_VOICES = [
  { id: "zh_female_qingxin", label: "清新女声" },
  { id: "zh_female_wanwanxiaohe_moon_bigtts", label: "湾湾小何" },
  { id: "zh_female_shaoergushi_mars_bigtts", label: "少儿故事" },
  { id: "zh_male_M392_conversation_wvae", label: "阳光男声" },
];

export function SettingsDrawer({ open, onClose, onUpdate }: SettingsDrawerProps) {
  const config = useAppStore((s) => s.config);
  const [local, setLocal] = useState<RuntimeConfig>(config);

  const handleSave = () => {
    onUpdate(local);
    onClose();
  };

  return (
    <>
      {/* 遮罩 */}
      <div
        className={clsx(
          "absolute inset-0 bg-midnight-800/60 backdrop-blur-sm transition-opacity duration-300 z-30",
          open ? "opacity-100" : "opacity-0 pointer-events-none",
        )}
        onClick={onClose}
      />

      {/* 抽屉 */}
      <div
        className={clsx(
          "absolute bottom-0 left-0 right-0 z-40",
          "glass rounded-t-3xl p-4 pb-6",
          "transition-transform duration-300 ease-out",
          open ? "translate-y-0" : "translate-y-full",
        )}
        style={{ maxHeight: "85%" }}
      >
        {/* 拖拽指示器 */}
        <div className="flex justify-center mb-3">
          <div className="w-10 h-1 rounded-full bg-moonlight/30" />
        </div>

        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-moonlight-300" />
            <h2 className="text-sm font-display text-moonlight-100">设置</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-full hover:bg-moonlight/10 transition"
          >
            <X className="w-4 h-4 text-moonlight/60" />
          </button>
        </div>

        <div className="space-y-3 overflow-y-auto no-scrollbar" style={{ maxHeight: "calc(85% - 60px)" }}>
          {/* LLM 模型（可输入自定义 ID） */}
          <Field label="AI 模型（可手动输入 ID）">
            <input
              type="text"
              list="llm-model-list"
              value={local.llmModelId}
              onChange={(e) => setLocal({ ...local, llmModelId: e.target.value })}
              placeholder="输入或选择模型 ID"
              className="w-full bg-midnight-600/60 text-moonlight-100 text-xs rounded-lg px-2 py-1.5 border border-moonlight/15 focus:outline-none focus:border-moonlight/40"
            />
            <datalist id="llm-model-list">
              {LLM_MODELS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </datalist>
          </Field>

          {/* TTS 音色 */}
          <Field label="语音音色">
            <select
              value={local.ttsVoiceId}
              onChange={(e) => setLocal({ ...local, ttsVoiceId: e.target.value })}
              className="w-full bg-midnight-600/60 text-moonlight-100 text-xs rounded-lg px-2 py-1.5 border border-moonlight/15 focus:outline-none focus:border-moonlight/40"
            >
              {TTS_VOICES.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </Field>

          {/* 语速 */}
          <Field label={`语速 (${local.ttsSpeed.toFixed(1)}x)`}>
            <input
              type="range"
              min="0.5"
              max="1.5"
              step="0.1"
              value={local.ttsSpeed}
              onChange={(e) => setLocal({ ...local, ttsSpeed: parseFloat(e.target.value) })}
              className="w-full accent-moonlight-300"
            />
          </Field>

          {/* 角色提示词 */}
          <Field label="角色人设">
            <textarea
              value={local.systemPrompt}
              onChange={(e) => setLocal({ ...local, systemPrompt: e.target.value })}
              rows={3}
              className="w-full bg-midnight-600/60 text-moonlight-100 text-xs rounded-lg px-2 py-1.5 border border-moonlight/15 focus:outline-none focus:border-moonlight/40 resize-none"
            />
          </Field>

          {/* 保存按钮 */}
          <button
            onClick={handleSave}
            className="w-full py-2 rounded-xl bg-moonlight/90 text-midnight-600 text-xs font-display font-medium active:scale-[0.98] transition"
          >
            保存
          </button>
        </div>
      </div>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[10px] text-moonlight/50 mb-1 font-display">
        {label}
      </label>
      {children}
    </div>
  );
}
