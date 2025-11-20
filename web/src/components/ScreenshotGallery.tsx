import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Dialog, DialogContent } from "./ui/dialog";
import type { SimulationScreenshot } from "../types/simulation";
import { XIcon } from "lucide-react";

interface ScreenshotGalleryProps {
  screenshots: SimulationScreenshot[];
  mode?: "grid" | "slideshow";
}

export default function ScreenshotGallery({
  screenshots,
  mode = "grid",
}: ScreenshotGalleryProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  const openFullscreen = (index: number) => {
    setSelectedIndex(index);
  };

  const closeFullscreen = () => {
    setSelectedIndex(null);
  };

  const goToPrevious = () => {
    if (selectedIndex !== null && selectedIndex > 0) {
      setSelectedIndex(selectedIndex - 1);
    }
  };

  const goToNext = () => {
    if (selectedIndex !== null && selectedIndex < screenshots.length - 1) {
      setSelectedIndex(selectedIndex + 1);
    }
  };

  if (screenshots.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Screenshots</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground text-center py-8">
            No screenshots available. Run a simulation in Visual or Screenshot
            mode to capture screenshots.
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Screenshots</CardTitle>
            <Badge variant="outline">{screenshots.length} captured</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {mode === "grid" ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {screenshots.map((screenshot, idx) => (
                <button
                  key={idx}
                  onClick={() => openFullscreen(idx)}
                  className="group relative aspect-video rounded-lg overflow-hidden border border-gray-200 hover:border-primary hover:shadow-md transition-all cursor-zoom-in"
                >
                  <img
                    src={screenshot.url}
                    alt={screenshot.step}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <span className="text-white text-xs font-medium px-2 py-1 bg-black/50 rounded">
                      Click to view
                    </span>
                  </div>
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2">
                    <p className="text-xs text-white font-medium truncate">
                      {screenshot.step}
                    </p>
                    <p className="text-xs text-gray-300">
                      {new Date(screenshot.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {screenshots.map((screenshot, idx) => (
                <div
                  key={idx}
                  className="border border-gray-200 rounded-lg overflow-hidden"
                >
                  <div className="bg-gray-100 px-3 py-2 flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {screenshot.step}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(screenshot.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <button
                    onClick={() => openFullscreen(idx)}
                    className="w-full hover:opacity-80 transition-opacity cursor-zoom-in"
                  >
                    <img
                      src={screenshot.url}
                      alt={screenshot.step}
                      className="w-full"
                    />
                  </button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Fullscreen Dialog */}
      <Dialog
        open={selectedIndex !== null}
        onOpenChange={(open) => !open && closeFullscreen()}
      >
        <DialogContent className="max-w-7xl w-[95vw] max-h-[95vh] p-0">
          {selectedIndex !== null && (
            <div className="relative h-full">
              {/* Close button */}
              <button
                onClick={closeFullscreen}
                className="absolute top-4 right-4 z-10 p-2 bg-black/50 hover:bg-black/70 text-white rounded-full transition-colors"
              >
                <XIcon className="w-5 h-5" />
              </button>

              {/* Navigation */}
              {selectedIndex > 0 && (
                <button
                  onClick={goToPrevious}
                  className="absolute left-4 top-1/2 -translate-y-1/2 z-10 p-3 bg-black/50 hover:bg-black/70 text-white rounded-full transition-colors"
                >
                  <svg
                    className="w-6 h-6"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 19l-7-7 7-7"
                    />
                  </svg>
                </button>
              )}
              {selectedIndex < screenshots.length - 1 && (
                <button
                  onClick={goToNext}
                  className="absolute right-4 top-1/2 -translate-y-1/2 z-10 p-3 bg-black/50 hover:bg-black/70 text-white rounded-full transition-colors"
                >
                  <svg
                    className="w-6 h-6"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </button>
              )}

              {/* Image */}
              <div className="p-6 h-full flex flex-col">
                <div className="bg-gray-100 px-4 py-3 rounded-t-lg">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium">
                      {screenshots[selectedIndex].step}
                    </h3>
                    <Badge variant="outline">
                      {selectedIndex + 1} of {screenshots.length}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {new Date(
                      screenshots[selectedIndex].timestamp
                    ).toLocaleString()}
                  </p>
                </div>
                <div className="flex-1 overflow-auto bg-gray-50 rounded-b-lg flex items-center justify-center">
                  <img
                    src={screenshots[selectedIndex].url}
                    alt={screenshots[selectedIndex].step}
                    className="max-w-full max-h-full object-contain"
                  />
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
