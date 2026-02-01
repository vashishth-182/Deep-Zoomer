import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import OpenSeadragon from "openseadragon";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  X,
  RotateCcw,
  Settings,
  Brain,
  Info,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface LocationState {
  imageUrl: string;
  thumbnailUrl?: string;
  title: string;
  description: string;
  nasaId: string;
}

interface MLModel {
  name: string;
  version: string;
  confidence: number;
  status: "active" | "loading" | "error";
}

interface FeatureDetection {
  type: string;
  confidence: number;
  bbox: [number, number, number, number];
  properties: Record<string, any>;
}

const AIEnhancedViewer = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as LocationState;
  const { toast } = useToast();

  const viewerRef = useRef<HTMLDivElement>(null);
  const osdRef = useRef<any>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [showMetadata, setShowMetadata] = useState(false);

  // AI Enhancement Controls
  const [enhanceEnabled, setEnhanceEnabled] = useState(true);
  const [labelsEnabled, setLabelsEnabled] = useState(true);
  const [confidenceThreshold, setConfidenceThreshold] = useState([0.5]);

  // ML Models Status
  const [mlModels] = useState<MLModel[]>([
    { name: "Real-ESRGAN", version: "1.0.0", confidence: 0.95, status: "active" },
    { name: "DnCNN", version: "1.0.0", confidence: 0.88, status: "active" },
    { name: "U-Net", version: "1.0.0", confidence: 0.92, status: "active" },
    { name: "ResNet", version: "1.0.0", confidence: 0.85, status: "active" },
  ]);

  // Feature Detection
  const [detectedFeatures, setDetectedFeatures] = useState<FeatureDetection[]>([]);
  const [showFeatureOverlay, setShowFeatureOverlay] = useState(true);

  if (!state) {
    navigate("/gallery");
    return null;
  }

  const imageUrl = state?.imageUrl || "/earth-image.jpg";

  // ✅ Initialize OpenSeadragon (Once per imageUrl)
  useEffect(() => {
    if (!viewerRef.current || !imageUrl) return;

    const container = viewerRef.current;
    if (osdRef.current) {
      osdRef.current.destroy();
    }

    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

    osdRef.current = OpenSeadragon({
      element: container,
      prefixUrl: "https://cdn.jsdelivr.net/npm/openseadragon@4.1/build/openseadragon/images/",
      tileSources: { type: "image", url: imageUrl }, // Start with standard view
      showNavigator: true,
      visibilityRatio: 1,
      maxZoomPixelRatio: 1.5,
      defaultZoomLevel: 1,
      maxZoomLevel: 30,
      constrainDuringPan: true,
      animationTime: 0.8,
      blendTime: 0.1,
      springStiffness: 10.0,
      imageSmoothingEnabled: true,
    });

    // Initial Metadata Fetch
    fetch(`${API_URL}/api/tiles/proxy/info.json?url=${encodeURIComponent(imageUrl)}`)
      .then(res => res.ok ? res.json() : null)
      .then(info => {
        if (info && info.width && info.height) {
          console.log("Deep Zoom Metadata Ready", info);
          updateTileSource(info);
        }
      })
      .catch(console.error);

    return () => {
      osdRef.current?.destroy();
    };
  }, [imageUrl]);

  // ✅ Smoothly update Tiled Source when AI settings change
  useEffect(() => {
    if (!osdRef.current || !imageUrl) return;

    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

    // Fetch info again or reuse (for now just refetch to get maxLevel)
    fetch(`${API_URL}/api/tiles/proxy/info.json?url=${encodeURIComponent(imageUrl)}`)
      .then(res => res.json())
      .then(info => {
        if (info.width) updateTileSource(info);
      })
      .catch(() => { });
  }, [enhanceEnabled, labelsEnabled, confidenceThreshold]);

  const updateTileSource = (info: any) => {
    if (!osdRef.current) return;
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

    const aiTileSource = {
      height: info.height,
      width: info.width,
      tileSize: 256,
      maxLevel: info.maxLevel || 14,
      getTileUrl: (level: number, x: number, y: number) => {
        return `${API_URL}/api/tiles/proxy/tile?url=${encodeURIComponent(imageUrl)}&z=${level}&x=${x}&y=${y}&enhance=${enhanceEnabled}&labels=${labelsEnabled}&confidence_threshold=${confidenceThreshold[0]}`;
      }
    };

    const world = osdRef.current.world;
    if (world.getItemCount() > 0) {
      world.getItemAt(0).setSource(aiTileSource);
    }
  };

  // Toggling enhancement now just triggers a re-render of the tiles via useEffect dependency
  const toggleEnhancement = () => {
    setEnhanceEnabled(!enhanceEnabled);
    toast({
      title: !enhanceEnabled ? "AI Enhancement Enabled" : "AI Enhancement Disabled",
      description: !enhanceEnabled ? "Image tiles will now be upscaled and denoised in real-time." : "Viewing original source quality.",
    });
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };


  // 🔳 Feature Overlay (for AI detection boxes)
  const renderFeatureOverlay = () => {
    if (!showFeatureOverlay || !detectedFeatures.length) return null;
    return (
      <div className="absolute inset-0 pointer-events-none z-10">
        {detectedFeatures.map((feature, index) => (
          <div
            key={index}
            className="absolute border-2 border-red-500 rounded"
            style={{
              left: `${feature.bbox[0]}px`,
              top: `${feature.bbox[1]}px`,
              width: `${feature.bbox[2] - feature.bbox[0]}px`,
              height: `${feature.bbox[3] - feature.bbox[1]}px`,
            }}
          >
            <div className="absolute -top-6 left-0 bg-red-500 text-white text-xs px-1 rounded">
              {feature.type}: {(feature.confidence * 100).toFixed(1)}%
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-background flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-card/50 backdrop-blur z-20">
        <div className="flex-1 min-w-0 mr-4">
          <h2 className="text-lg font-semibold truncate">{state.title}</h2>
          <p className="text-sm text-muted-foreground truncate">
            NASA ID: {state.nasaId}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowControls(!showControls)}
          >
            <Settings className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" onClick={() => navigate("/gallery")}>
            <X className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Viewer */}
      <div className="flex-1 relative overflow-hidden">
        <div ref={viewerRef} className="w-full h-full" />

        {/* Zoom Controls */}
        <div className="absolute bottom-4 right-4 z-30 flex flex-col gap-2 bg-card/40 backdrop-blur-lg p-2 rounded-lg border border-border">
          <Button
            size="icon"
            onClick={() => {
              osdRef.current?.viewport?.zoomBy(1.2);
              osdRef.current?.viewport?.applyConstraints();
            }}
            className="bg-primary/30 hover:bg-primary/50"
          >
            <ZoomIn className="w-5 h-5" />
          </Button>
          <Button
            size="icon"
            onClick={() => {
              osdRef.current?.viewport?.zoomBy(0.8);
              osdRef.current?.viewport?.applyConstraints();
            }}
            className="bg-primary/30 hover:bg-primary/50"
          >
            <ZoomOut className="w-5 h-5" />
          </Button>
          <Button
            size="icon"
            onClick={() => osdRef.current?.viewport?.goHome()}
            className="bg-secondary/30 hover:bg-secondary/50"
          >
            <RotateCcw className="w-5 h-5" />
          </Button>
          <Button
            size="icon"
            onClick={toggleFullscreen}
            className="bg-secondary/30 hover:bg-secondary/50"
          >
            <Maximize2 className="w-5 h-5" />
          </Button>
        </div>

        {/* Feature Overlay */}
        {renderFeatureOverlay()}
      </div>

      {/* Bottom Instructions */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-20 pointer-events-none">
        <div className="bg-gradient-to-r from-primary/20 via-accent/20 to-primary/20 backdrop-blur-lg rounded-lg px-6 py-3 border border-primary/30">
          <p className="text-sm font-medium bg-gradient-to-r from-primary via-accent to-primary-glow bg-clip-text text-transparent">
            🔍 Scroll to zoom • ✋ Drag to pan • 🧠 AI enhancement auto-refreshes on zoom
          </p>
        </div>
      </div>
    </div>
  );
};

export default AIEnhancedViewer;
