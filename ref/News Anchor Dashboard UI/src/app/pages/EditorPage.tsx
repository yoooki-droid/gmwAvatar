import { useState } from "react";
import { Sparkles, Quote, Save } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";

export function EditorPage() {
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [speakerName, setSpeakerName] = useState("");
  const [originalSummary, setOriginalSummary] = useState("");
  const [broadcastScript, setBroadcastScript] = useState(
    "Good evening, I'm [Speaker Name], and welcome to tonight's broadcast. In today's top stories, we bring you the most important updates from around the world.\n\nOur lead story tonight focuses on [Main Topic]. Sources indicate that [Key Details]. This development comes after weeks of speculation and marks a significant turning point in [Context].\n\nExperts are weighing in on what this means for the future, with many suggesting that [Expert Opinion]. The implications could be far-reaching, affecting [Impact Areas].\n\nWe'll continue to monitor this situation and bring you updates as they develop. That's all for tonight's broadcast. I'm [Speaker Name], thank you for joining us."
  );
  const [highlights, setHighlights] = useState([
    "Key announcement regarding policy changes will take effect next quarter",
    "Industry leaders collaborate on new sustainability initiative",
  ]);

  const handleHighlightChange = (index: number, value: string) => {
    const newHighlights = [...highlights];
    newHighlights[index] = value;
    setHighlights(newHighlights);
  };

  return (
    <div className="h-[calc(100vh-73px)] overflow-hidden">
      <div className="h-full flex">
        {/* Left Side - Input Section */}
        <div className="w-[40%] bg-gray-100 p-8 overflow-y-auto">
          <div className="max-w-2xl">
            <h2 className="text-2xl font-semibold text-black mb-6">Content Input</h2>

            <div className="space-y-6">
              {/* News Title */}
              <div className="space-y-2">
                <Label htmlFor="title" className="text-sm font-medium text-gray-700">
                  News Title
                </Label>
                <Input
                  id="title"
                  placeholder="Enter news title..."
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="bg-white border-gray-300"
                />
              </div>

              {/* Date */}
              <div className="space-y-2">
                <Label htmlFor="date" className="text-sm font-medium text-gray-700">
                  Date
                </Label>
                <Input
                  id="date"
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="bg-white border-gray-300"
                />
              </div>

              {/* Speaker Name */}
              <div className="space-y-2">
                <Label htmlFor="speaker" className="text-sm font-medium text-gray-700">
                  Speaker Name
                </Label>
                <Input
                  id="speaker"
                  placeholder="Enter speaker name..."
                  value={speakerName}
                  onChange={(e) => setSpeakerName(e.target.value)}
                  className="bg-white border-gray-300"
                />
              </div>

              {/* Original Meeting Summary */}
              <div className="space-y-2">
                <Label htmlFor="summary" className="text-sm font-medium text-gray-700">
                  Original Meeting Summary
                </Label>
                <Textarea
                  id="summary"
                  placeholder="Paste or type the original meeting summary here..."
                  value={originalSummary}
                  onChange={(e) => setOriginalSummary(e.target.value)}
                  className="bg-white border-gray-300 min-h-[400px] resize-none"
                />
              </div>

              <Button
                variant="outline"
                className="w-full bg-violet-600 hover:bg-violet-700 text-white border-violet-600"
              >
                <Sparkles size={16} className="mr-2" />
                Generate Broadcast Script
              </Button>
            </div>
          </div>
        </div>

        {/* Right Side - AI Output Section */}
        <div className="w-[60%] bg-white flex flex-col">
          {/* Top Bar with Actions */}
          <div className="flex items-center justify-between px-8 py-4 border-b border-gray-200">
            <h2 className="text-2xl font-semibold text-black">AI Output</h2>
            <div className="flex items-center gap-3">
              <Button variant="outline" className="border-gray-300">
                <Save size={16} className="mr-2" />
                Save Draft
              </Button>
              <Button className="bg-black hover:bg-gray-800 text-white">
                Publish
              </Button>
            </div>
          </div>

          {/* Scrollable Content */}
          <div className="flex-1 overflow-y-auto p-8">
            <div className="max-w-3xl space-y-8">
              {/* Broadcast Script */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Sparkles size={18} className="text-violet-600" />
                  <Label className="text-sm font-medium text-gray-700">
                    Broadcast Script (AI Rewritten)
                  </Label>
                </div>
                <Textarea
                  value={broadcastScript}
                  onChange={(e) => setBroadcastScript(e.target.value)}
                  className="min-h-[320px] text-base leading-relaxed resize-none border-gray-300"
                />
              </div>

              {/* Highlights */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-black">Highlights</h3>
                <div className="space-y-3">
                  {highlights.map((highlight, index) => (
                    <div
                      key={index}
                      className="bg-amber-50 border border-amber-200 rounded-lg p-4"
                    >
                      <div className="flex gap-3">
                        <Quote size={20} className="text-amber-600 flex-shrink-0 mt-1" />
                        <Textarea
                          value={highlight}
                          onChange={(e) => handleHighlightChange(index, e.target.value)}
                          className="border-0 bg-transparent p-0 text-base resize-none min-h-[60px] focus-visible:ring-0"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
