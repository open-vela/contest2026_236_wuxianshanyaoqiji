"""Render the architecture and protocol flow used in the technical report."""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/contest/template-review-assets'
OUT.mkdir(parents=True, exist_ok=True)
FONT = Path('C:/Windows/Fonts/msyh.ttc')
if not FONT.exists():
    raise SystemExit('Set FONT to an installed CJK font before rendering')

def canvas(title, size):
    im = Image.new('RGB', size, 'white')
    d = ImageDraw.Draw(im)
    d.text((44, 25), title, font=ImageFont.truetype(str(FONT), 36), fill='#24344B')
    return im, d

def text(d, xy, value, size=25, color='#24344B', anchor=None):
    d.text(xy, value, font=ImageFont.truetype(str(FONT), size), fill=color, anchor=anchor)

def box(d, rect, title, lines, fill='#F1F5FA'):
    x0,y0,x1,y1=rect
    d.rounded_rectangle(rect, radius=16, fill=fill, outline='#A6B6CB', width=2)
    text(d,(x0+22,y0+19),title,29)
    for i,line in enumerate(lines):text(d,(x0+22,y0+68+i*38),line,24)

def arrow(d, points, color='#55708E', both=False):
    d.line(points, fill=color, width=4)
    def head(a,b):
        angle=math.atan2(b[1]-a[1],b[0]-a[0]);length=14
        d.polygon([b,(b[0]-length*math.cos(angle-.5),b[1]-length*math.sin(angle-.5)),
                   (b[0]-length*math.cos(angle+.5),b[1]-length*math.sin(angle+.5))],fill=color)
    head(points[-2],points[-1])
    if both:head(points[1],points[0])

im,d=canvas('系统架构：openvela 主终端 + ESP-IDF 外部伙伴',(1500,880))
box(d,(405,110,1100,285),'云端服务',['阿里 Paraformer ASR / Qwen 3.1 TTS','火山豆包拟人模型 · 文字生成'])
box(d,(405,385,1100,600),'电脑协调服务 · Python + 语音 C 后端',
    ['角色与轮次 / 完成确认 / 最终总结','双机文字生成；Passport 的识别与合成','必须持续运行，不把这些能力计为板端推理'])
box(d,(40,665,720,835),'Gemini-S1 · openvela / NuttX',
    ['官方 ai_agent / LVGL / 媒体链路','实体 ENTER、录音播放、动画、联动客户端'],'#EDF6F5')
box(d,(790,665,1460,835),'AI Passport · ESP-IDF / FreeRTOS',
    ['小澄 UI、按键、I2S、Wi-Fi、NVS','上传录音 PCM；接收文字与播放 PCM'],'#F5F0FA')
arrow(d,[(750,285),(750,385)],both=True);text(d,(780,318),'HTTPS/WSS · Key 鉴权',24)
arrow(d,[(570,600),(570,665)],both=True);text(d,(60,610),'LAN HTTP：文字 / 确认',23)
arrow(d,[(945,600),(945,665)],both=True);text(d,(980,610),'LAN HTTP：文字 / PCM / 确认',23)
arrow(d,[(200,665),(200,195),(405,195)],both=True)
text(d,(43,330),'Gemini 本机语音',23);text(d,(43,367),'及单人会话直连云端',23)
im.save(OUT/'architecture.png')

im,d=canvas('双机有限轮次流程：只汇总已确认完成的对话',(1500,1070))
box(d,(80,105,1050,215),'两端在线且就绪 → 用户/配置允许启动',['建立 epoch；重置本轮成功历史'])
box(d,(80,280,1050,390),'根据已完成记录生成下一句',['按角色交替；每条命令分配 seq'])
box(d,(80,455,1050,565),'两屏显示 → 发言设备合成并播放',['双机通过文本协议联动，不使用麦克风互听'])
box(d,(80,630,1050,740),'等待双方对当前 seq 返回成功确认',['完成后才计入成功历史；不足 6 次则继续'])
box(d,(80,805,1050,940),'完成 6 次发言 → 生成总结 → 确认结束',['总结仅基于已完成内容，由 Gemini 朗读','两屏保留结果，用户决定采用哪些建议'],'#EDF6F5')
for start,end in [(215,280),(390,455),(565,630),(740,805)]:arrow(d,[(560,start),(560,end)])
arrow(d,[(80,685),(35,685),(35,335),(80,335)])
box(d,(1100,320,1470,720),'异常出口',
    ['用户取消 / 伙伴离线','播放失败 / 超时','云端请求失败','','停止本轮，递增 epoch','迟到结果作废','失败句不进入总结'],'#FFF2EA')
arrow(d,[(1050,510),(1100,510)],color='#A66042')
text(d,(80,990),'图中为实现机制；阈值和状态机测试不等于长期实机稳定性通过。',26)
im.save(OUT/'flow.png')
im,d=canvas('从相遇到小结：当前功能与后续 NFC 入口',(1500,980))
box(d,(50,110,710,290),'当前入口 · 已实现',
    ['两端同网、预先配置并就绪','首次就绪自动开始 / 长按中键确认'],'#EDF6F5')
box(d,(790,110,1450,290),'后续入口 · NFC 规划',
    ['碰一碰 → 伙伴识别 → 就绪检查','硬件、驱动与触发验证尚未实现'],'#FFF2EA')
box(d,(50,410,480,625),'双角色交流',
    ['围绕同一话题接续发言','发言者朗读、另一端显示','双方完成确认后推进'])
box(d,(550,410,970,625),'本轮总结',
    ['完成六次发言后整理','主题 + 最多两个建议','一个交给用户的问题'])
box(d,(1040,410,1450,625),'用户选择',
    ['两屏保留小结','Gemini 朗读结果','停止 / 再开一轮 / 问答'])
arrow(d,[(370,290),(370,410)])
arrow(d,[(1120,290),(1120,345),(390,345),(390,410)],color='#A66042')
arrow(d,[(480,515),(550,515)])
arrow(d,[(970,515),(1040,515)])
box(d,(50,760,1450,925),'单人语音 · 独立入口',
    ['按键录音 → 识别 → 文本回复 → 合成播放 → 成功后加入近期问答历史',
     '主动录音先停止双机；语音内容不会自动变成两端公共话题'],'#F5F0FA')
arrow(d,[(1240,625),(1240,760)])
text(d,(50,660),'NFC 规划复用同一对话与总结流程；当前录像不作为 NFC 感应测试证据。',25)
im.save(OUT/'encounter.png')
print('Rendered architecture.png, flow.png and encounter.png')
