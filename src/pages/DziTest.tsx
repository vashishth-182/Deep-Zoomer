"use client";
import { useEffect, useRef } from "react";

const DziTest = () => {
  const viewerRef = useRef<HTMLDivElement>(null);
  const osdRef = useRef<any>(null);

  useEffect(() => {
    const loadViewer = async () => {
      if (!viewerRef.current) return;

      const container = viewerRef.current;
      container.style.position = "relative";

      // ✅ dynamically import OpenSeadragon here
      const OpenSeadragonModule = await import("openseadragon");
      const OpenSeadragon = OpenSeadragonModule.default ?? OpenSeadragonModule;

      // Test with a simple DZI file
      const testDziUrl = "/earth_tiles.dzi";

      osdRef.current = OpenSeadragon({
        element: container,
        prefixUrl:
          "https://cdn.jsdelivr.net/npm/openseadragon@4.1/build/openseadragon/images/",
        tileSources: testDziUrl,
        showNavigator: true,
        showNavigationControl: true,
        showFullPageControl: true,
        showZoomControl: true,
        showHomeControl: true,
        showRotationControl: true,

        // Basic configuration
        maxZoomPixelRatio: 2,
        minZoomImageRatio: 0.1,
        maxZoomLevel: 20,
        minZoomLevel: 0,

        // Tile configuration
        tileSize: 256,
        imageLoaderLimit: 3,
        timeout: 30000,

        // Smooth controls
        springStiffness: 8.0,
        animationTime: 0.8,
        blendTime: 0.05,
        constrainDuringPan: false,

        // Gesture settings
        gestureSettingsMouse: {
          scrollToZoom: true,
          clickToZoom: true,
          dblClickToZoom: true,
          flickEnabled: true,
          pinchToZoom: true,
          zoomBy: 1.2,
        },
        gestureSettingsTouch: {
          scrollToZoom: true,
          clickToZoom: true,
          dblClickToZoom: true,
          flickEnabled: true,
          pinchToZoom: true,
          zoomBy: 1.2,
        },

        // Image quality
        loadTilesWithAjax: true,
        ajaxWithCredentials: false,

        // Retry configuration
        tileRetryMax: 5,
        tileRetryDelay: 2000,
        tileLoadTimeout: 60000,

        // Performance
        useCanvas: true,
        preserveViewport: true,
        preserveImageSize: true,
      });

      const viewer = osdRef.current;

      // Add event handlers for debugging
      viewer.addHandler("tile-loaded", (event: any) => {
        console.log("Tile loaded successfully:", event);
      });

      viewer.addHandler("tile-load-failed", (event: any) => {
        console.error("Tile load failed:", event);
      });

      viewer.addHandler("tile-drawing", (event: any) => {
        console.log("Drawing tile:", event);
      });

      viewer.addHandler("tile-drawn", (event: any) => {
        console.log("Tile drawn:", event);
      });

      viewer.addHandler("open", (event: any) => {
        console.log("Viewer opened:", event);
      });

      viewer.addHandler("error", (event: any) => {
        console.error("Viewer error:", event);
      });
    };

    loadViewer();

    return () => {
      if (osdRef.current && osdRef.current.destroy) {
        osdRef.current.destroy();
      }
    };
  }, []);

  return (
    <div className="min-h-screen bg-background pt-28">
      <div className="container mx-auto px-4">
        <h1 className="text-3xl font-bold mb-4">DZI Test Viewer</h1>
        <p className="text-muted-foreground mb-4">
          Testing DZI tile loading with console logging
        </p>

        <div className="bg-card border rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold mb-2">Test Information</h2>
          <ul className="text-sm space-y-1">
            <li>• DZI File: /earth_tiles.dzi</li>
            <li>• Tile Size: 256px</li>
            <li>• Format: JPG</li>
            <li>• Check browser console for tile loading events</li>
          </ul>
        </div>

        <div
          ref={viewerRef}
          className="w-full h-96 border border-border rounded-lg bg-muted"
        />

        <div className="mt-4 text-sm text-muted-foreground">
          <p>If tiles fail to load, check:</p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>Browser console for error messages</li>
            <li>Network tab for failed requests</li>
            <li>That DZI files exist in /public directory</li>
            <li>That tile directories contain the expected files</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default DziTest;
