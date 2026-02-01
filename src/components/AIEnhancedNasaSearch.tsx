import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Search,
  Filter,
  Star,
  Download,
  Eye,
  Brain,
  Zap,
  AlertCircle,
  CheckCircle,
  Clock,
  Image as ImageIcon,
  Video,
  FileText
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface NasaItem {
  data: {
    title: string;
    nasa_id: string;
    description?: string;
    date_created: string;
    keywords?: string[];
    media_type: string;
  }[];
  links?: {
    href: string;
    render: string;
  }[];
}

interface NasaApiResponse {
  collection: {
    items: NasaItem[];
    metadata: {
      total_hits: number;
    };
  };
}

interface SearchFilters {
  mediaType: string;
  yearRange: [number, number];
  keywords: string[];
  hasHighRes: boolean;
  aiEnhanced: boolean;
}

const AIEnhancedNasaSearch = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [searchTerm, setSearchTerm] = useState("Earth");
  const [images, setImages] = useState<NasaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalHits, setTotalHits] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedImage, setSelectedImage] = useState<NasaItem | null>(null);

  // AI Enhancement Features
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({
    mediaType: "image",
    yearRange: [2000, 2024],
    keywords: [],
    hasHighRes: false,
    aiEnhanced: false
  });

  // AI Processing Status
  const [processingStatus, setProcessingStatus] = useState<Record<string, string>>({});
  const [processingProgress, setProcessingProgress] = useState<Record<string, number>>({});

  const [aiCapabilities, setAiCapabilities] = useState({
    superResolution: true,
    denoising: true,
    featureDetection: true,
    classification: true
  });

  const fetchImages = async (query: string, page: number = 1) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `https://images-api.nasa.gov/search?q=${query}&media_type=image&page=${page}`
      );

      if (!response.ok) throw new Error("Failed to fetch NASA images");

      const data: NasaApiResponse = await response.json();

      // Filter by additional criteria
      let filteredImages = data.collection.items.filter((item) => {
        const title = item.data[0].title.toLowerCase();
        const description = item.data[0].description?.toLowerCase() || "";
        const searchQuery = query.toLowerCase();

        return title.includes(searchQuery) || description.includes(searchQuery);
      });

      // Apply AI enhancement filter
      if (filters.aiEnhanced) {
        filteredImages = filteredImages.filter(item => {
          // Check if image has AI enhancement available
          return checkAIEnhancementAvailable(item);
        });
      }

      setImages(filteredImages);
      setTotalHits(data.collection.metadata.total_hits);

      // Check AI processing status for each image
      checkAIProcessingStatus(filteredImages);

    } catch (err: any) {
      setError(err.message);
      toast({
        title: "Search Error",
        description: err.message,
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const checkAIEnhancementAvailable = (item: NasaItem): boolean => {
    // Mock check - in real implementation, this would query the backend
    const nasaId = item.data[0].nasa_id;
    return nasaId.length > 5; // Simple heuristic
  };

  const checkAIProcessingStatus = async (items: NasaItem[]) => {
    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

    for (const item of items) {
      const nasaId = item.data[0].nasa_id;
      try {
        const response = await fetch(`${API_URL}/api/ml/status/${nasaId}`);
        if (response.ok) {
          const data = await response.json();
          setProcessingStatus(prev => ({ ...prev, [nasaId]: data.status }));
          setProcessingProgress(prev => ({ ...prev, [nasaId]: data.progress || 0 }));

          // Continue polling if still processing
          if (data.status === 'processing') {
            setTimeout(() => checkAIProcessingStatus([item]), 4000);
          }
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }
  };

  const handleImageClick = (item: NasaItem) => {
    const imageUrl = item.links?.[0]?.href || "";
    const nasaId = item.data[0].nasa_id;

    if (!imageUrl) {
      toast({
        title: "No Image Available",
        description: "This item doesn't have an associated image.",
        variant: "destructive"
      });
      return;
    }

    // Navigate to AI-enhanced viewer
    navigate("/ai-viewer", {
      state: {
        imageUrl: imageUrl,
        title: item.data[0].title,
        description: item.data[0].description || "",
        nasaId: nasaId,
        aiEnhanced: filters.aiEnhanced,
        processingStatus: processingStatus[nasaId]
      }
    });
  };

  const requestAIEnhancement = async (nasaId: string) => {
    try {
      setProcessingStatus(prev => ({ ...prev, [nasaId]: 'processing' }));
      const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

      const response = await fetch(`${API_URL}/api/ml/precompute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_id: nasaId,
          image_url: images.find(img => img.data[0].nasa_id === nasaId)?.links?.[0]?.href,
          zoom_levels: [10, 11, 12],
          operations: ['sr', 'denoise']
        })
      });

      if (response.ok) {
        toast({
          title: "AI Enhancement Started",
          description: "Processing your image with AI models. This may take a few minutes.",
        });
        setProcessingStatus(prev => ({ ...prev, [nasaId]: 'processing' }));
      }
    } catch (error) {
      toast({
        title: "Enhancement Failed",
        description: "Could not start AI processing.",
        variant: "destructive"
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'processing':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Zap className="w-4 h-4 text-blue-500" />;
    }
  };

  const getStatusText = (status: string, nasaId: string) => {
    switch (status) {
      case 'processing':
        return `Processing ${processingProgress[nasaId] || 0}%`;
      case 'completed':
        return 'AI Enhanced';
      case 'error':
        return 'Error';
      default:
        return 'Available';
    }
  };

  useEffect(() => {
    fetchImages(searchTerm);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground pt-28 px-4 md:px-16 transition-colors duration-300">
      <div className="container mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-clip-text text-transparent bg-aurora-gradient">
            AI-Enhanced NASA Image Search
          </h1>
          <p className="text-muted-foreground text-lg mb-8">
            Discover and explore NASA imagery with AI-powered super-resolution, denoising, and feature detection
          </p>
        </div>

        {/* Search and Filters */}
        <div className="flex flex-col md:flex-row justify-center items-center gap-4 mb-8">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input
              type="text"
              placeholder="Search NASA images..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 w-full"
            />
          </div>
          <Button
            onClick={() => fetchImages(searchTerm)}
            disabled={loading}
            className="px-8 py-3"
          >
            {loading ? "Searching..." : "Search"}
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="px-4"
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
          </Button>
        </div>

        {/* AI Capabilities Banner */}
        <div className="mb-8 p-4 bg-gradient-to-r from-primary/10 via-accent/10 to-primary/10 rounded-lg border border-primary/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Brain className="w-6 h-6 text-primary" />
              <div>
                <h3 className="font-semibold">AI Enhancement Available</h3>
                <p className="text-sm text-muted-foreground">
                  Super-resolution • Denoising • Feature Detection • Classification
                </p>
              </div>
            </div>
            <Badge variant="secondary" className="bg-primary/20 text-primary">
              Beta
            </Badge>
          </div>
        </div>

        {/* Filters Panel */}
        {showFilters && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>Search Filters</CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="basic" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="basic">Basic</TabsTrigger>
                  <TabsTrigger value="ai">AI Features</TabsTrigger>
                  <TabsTrigger value="advanced">Advanced</TabsTrigger>
                </TabsList>

                <TabsContent value="basic" className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium">Media Type</label>
                      <select
                        value={filters.mediaType}
                        onChange={(e) => setFilters(prev => ({ ...prev, mediaType: e.target.value }))}
                        className="w-full p-2 border rounded"
                      >
                        <option value="image">Images</option>
                        <option value="video">Videos</option>
                        <option value="audio">Audio</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-sm font-medium">Year Range</label>
                      <div className="flex gap-2">
                        <Input
                          type="number"
                          value={filters.yearRange[0]}
                          onChange={(e) => setFilters(prev => ({
                            ...prev,
                            yearRange: [parseInt(e.target.value), prev.yearRange[1]]
                          }))}
                          className="w-20"
                        />
                        <Input
                          type="number"
                          value={filters.yearRange[1]}
                          onChange={(e) => setFilters(prev => ({
                            ...prev,
                            yearRange: [prev.yearRange[0], parseInt(e.target.value)]
                          }))}
                          className="w-20"
                        />
                      </div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="ai" className="space-y-4">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>High Resolution Available</span>
                      <input
                        type="checkbox"
                        checked={filters.hasHighRes}
                        onChange={(e) => setFilters(prev => ({ ...prev, hasHighRes: e.target.checked }))}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <span>AI Enhancement Available</span>
                      <input
                        type="checkbox"
                        checked={filters.aiEnhanced}
                        onChange={(e) => setFilters(prev => ({ ...prev, aiEnhanced: e.target.checked }))}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex items-center gap-2">
                        <input type="checkbox" checked={aiCapabilities.superResolution} readOnly />
                        <span className="text-sm">Super Resolution</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <input type="checkbox" checked={aiCapabilities.denoising} readOnly />
                        <span className="text-sm">Denoising</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <input type="checkbox" checked={aiCapabilities.featureDetection} readOnly />
                        <span className="text-sm">Feature Detection</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <input type="checkbox" checked={aiCapabilities.classification} readOnly />
                        <span className="text-sm">Classification</span>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="advanced" className="space-y-4">
                  <div>
                    <label className="text-sm font-medium">Keywords</label>
                    <Input
                      placeholder="Enter keywords separated by commas"
                      value={filters.keywords.join(", ")}
                      onChange={(e) => setFilters(prev => ({
                        ...prev,
                        keywords: e.target.value.split(",").map(k => k.trim()).filter(k => k)
                      }))}
                    />
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        )}

        {/* Status */}
        {loading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-lg text-muted-foreground">Searching NASA database...</p>
          </div>
        )}

        {error && (
          <div className="text-center py-8">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-lg text-red-500">{error}</p>
          </div>
        )}

        {!loading && images.length === 0 && !error && (
          <div className="text-center py-8">
            <ImageIcon className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-lg text-muted-foreground">No images found.</p>
          </div>
        )}

        {/* Results */}
        {!loading && images.length > 0 && (
          <>
            <div className="flex justify-between items-center mb-6">
              <p className="text-muted-foreground">
                Found {totalHits} images • Showing {images.length}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  <Download className="w-4 h-4 mr-2" />
                  Export
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {images.map((item, idx) => {
                const imageUrl = item.links?.[0]?.href || "";
                const nasaId = item.data[0].nasa_id;
                const status = processingStatus[nasaId] || 'available';

                return (
                  <Card
                    key={idx}
                    className="group cursor-pointer overflow-hidden border-border hover:border-primary transition-all duration-300 hover:shadow-cosmic"
                    onClick={() => handleImageClick(item)}
                  >
                    <CardContent className="p-0">
                      <div className="relative aspect-square overflow-hidden bg-muted">
                        {imageUrl ? (
                          <img
                            src={imageUrl}
                            alt={item.data[0]?.title || "NASA Image"}
                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                          />
                        ) : (
                          <div className="w-full h-full bg-gray-700 flex items-center justify-center text-gray-300">
                            <ImageIcon className="w-8 h-8" />
                          </div>
                        )}

                        {/* AI Status Overlay */}
                        <div className="absolute top-2 right-2">
                          <Badge
                            variant={status === 'completed' ? 'default' : 'secondary'}
                            className="bg-card/90 backdrop-blur"
                          >
                            {getStatusIcon(status)}
                            <span className="ml-1">{getStatusText(status, nasaId)}</span>
                          </Badge>
                        </div>

                        {/* Hover Overlay */}
                        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                          <div className="absolute bottom-0 left-0 right-0 p-4">
                            <h3 className="font-semibold text-sm line-clamp-2 mb-2">
                              {item.data[0]?.title || "Untitled"}
                            </h3>
                            <div className="flex items-center justify-between">
                              <p className="text-xs text-muted-foreground">
                                {new Date(item.data[0]?.date_created).toLocaleDateString()}
                              </p>
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  requestAIEnhancement(nasaId);
                                }}
                                className="opacity-0 group-hover:opacity-100 transition-opacity"
                              >
                                <Brain className="w-3 h-3 mr-1" />
                                Enhance
                              </Button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default AIEnhancedNasaSearch;
