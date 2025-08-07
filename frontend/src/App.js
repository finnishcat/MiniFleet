import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [containers, setContainers] = useState([]);
  const [images, setImages] = useState([]);
  const [dockerStatus, setDockerStatus] = useState(null);
  const [backgroundImage, setBackgroundImage] = useState('');
  const [selectedContainer, setSelectedContainer] = useState(null);
  const [containerStats, setContainerStats] = useState({});
  const [containerLogs, setContainerLogs] = useState('');
  const [containerYaml, setContainerYaml] = useState('');
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [detailTab, setDetailTab] = useState('overview');
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [imageUpdates, setImageUpdates] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  // Fetch background image on component mount
  useEffect(() => {
    fetchBackgroundImage();
  }, []);

  // Fetch notifications
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Check for image updates periodically
  useEffect(() => {
    if (images.length > 0 && dockerStatus?.status !== 'demo') {
      checkImageUpdates();
    }
  }, [images]);

  const fetchBackgroundImage = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/background-image`);
      const data = await response.json();
      setBackgroundImage(data.image_url);
    } catch (err) {
      console.error('Failed to fetch background image:', err);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // For demo purposes, if Docker is not available, show mock data
      const statusResponse = await fetch(`${backendUrl}/api/docker/status`);
      
      if (statusResponse.status === 503) {
        // Show mock data for demo
        console.log('Docker not available, showing demo data...');
        setDockerStatus({
          status: "demo",
          containers_running: 3,
          containers_stopped: 1,
          images: 5,
          server_version: "Demo Mode",
          architecture: "x86_64"
        });
        
        // Mock containers
        setContainers([
          {
            id: "demo-nginx",
            name: "nginx-web",
            image: "nginx:latest",
            status: "running",
            state: "running",
            uptime: "2h 15m",
            short_id: "abc123"
          },
          {
            id: "demo-postgres",
            name: "postgres-db",
            image: "postgres:14",
            status: "running",
            state: "running",
            uptime: "1d 5h",
            short_id: "def456"
          },
          {
            id: "demo-redis",
            name: "redis-cache",
            image: "redis:7",
            status: "running",
            state: "running",
            uptime: "3h 22m",
            short_id: "ghi789"
          },
          {
            id: "demo-stopped",
            name: "old-container",
            image: "ubuntu:20.04",
            status: "exited",
            state: "exited",
            uptime: null,
            short_id: "jkl012"
          }
        ]);
        
        // Mock images
        setImages([
          {
            id: "img-nginx",
            short_id: "sha256:abc123",
            tag: "nginx:latest",
            created: "2024-01-15T10:30:00Z",
            size: 142000000,
            virtual_size: 142000000,
            architecture: "amd64"
          },
          {
            id: "img-postgres",
            short_id: "sha256:def456",
            tag: "postgres:14",
            created: "2024-01-10T08:15:00Z",
            size: 374000000,
            virtual_size: 374000000,
            architecture: "amd64"
          },
          {
            id: "img-redis",
            short_id: "sha256:ghi789",
            tag: "redis:7",
            created: "2024-01-08T14:22:00Z",
            size: 117000000,
            virtual_size: 117000000,
            architecture: "amd64"
          },
          {
            id: "img-node",
            short_id: "sha256:jkl012",
            tag: "node:18-alpine",
            created: "2024-01-05T16:45:00Z",
            size: 169000000,
            virtual_size: 169000000,
            architecture: "amd64"
          },
          {
            id: "img-ubuntu",
            short_id: "sha256:mno345",
            tag: "ubuntu:20.04",
            created: "2024-01-01T12:00:00Z",
            size: 72000000,
            virtual_size: 72000000,
            architecture: "amd64"
          }
        ]);
        
        setLoading(false);
        return;
      }

      // If Docker is available, fetch real data
      if (!statusResponse.ok) throw new Error('Failed to fetch Docker status');
      const statusData = await statusResponse.json();
      setDockerStatus(statusData);

      // Fetch containers
      const containersResponse = await fetch(`${backendUrl}/api/containers`);
      if (!containersResponse.ok) throw new Error('Failed to fetch containers');
      const containersData = await containersResponse.json();
      setContainers(containersData.containers);

      // Fetch images
      const imagesResponse = await fetch(`${backendUrl}/api/images`);
      if (!imagesResponse.ok) throw new Error('Failed to fetch images');
      const imagesData = await imagesResponse.json();
      setImages(imagesData.images);

    } catch (err) {
      setError(err.message);
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchContainerStats = async (containerId) => {
    try {
      const response = await fetch(`${backendUrl}/api/containers/${containerId}/stats`);
      const data = await response.json();
      setContainerStats(data);
    } catch (err) {
      console.error('Failed to fetch container stats:', err);
    }
  };

  const fetchContainerLogs = async (containerId) => {
    try {
      const response = await fetch(`${backendUrl}/api/containers/${containerId}/logs`);
      const data = await response.json();
      setContainerLogs(data.logs);
    } catch (err) {
      console.error('Failed to fetch container logs:', err);
    }
  };

  const handleContainerClick = async (container) => {
    setSelectedContainer(container);
    setShowDetailModal(true);
    await fetchContainerStats(container.id);
    await fetchContainerLogs(container.id);
  };

  const getContainerIcon = (imageName) => {
    const image = imageName.toLowerCase();
    if (image.includes('nginx')) return '🌐';
    if (image.includes('postgres') || image.includes('mysql')) return '🗄️';
    if (image.includes('redis')) return '⚡';
    if (image.includes('mongo')) return '🍃';
    if (image.includes('docker')) return '🐳';
    if (image.includes('node')) return '📗';
    if (image.includes('python')) return '🐍';
    if (image.includes('java')) return '☕';
    if (image.includes('golang') || image.includes('go:')) return '🐹';
    return '📦';
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'text-green-500';
      case 'paused': return 'text-yellow-500';
      case 'exited': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatUptime = (uptime) => {
    if (!uptime) return 'N/A';
    return uptime;
  };

  if (loading && !dockerStatus) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading Docker Monitor...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div 
        className="min-h-screen bg-cover bg-center bg-fixed flex items-center justify-center"
        style={{
          backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)), url(${backgroundImage || 'https://images.unsplash.com/photo-1661064941810-7a62f443fdb1'})`
        }}
      >
        <div className="bg-gray-800 bg-opacity-90 backdrop-blur-sm rounded-lg p-8 max-w-md text-center">
          <div className="text-6xl mb-4">🐳</div>
          <h1 className="text-2xl font-bold text-white mb-4">Docker Monitor</h1>
          <div className="text-red-400 mb-4">
            <p className="text-lg font-semibold">Docker Not Available</p>
            <p className="text-sm">Docker is not running on this server</p>
          </div>
          <div className="text-gray-300 text-sm">
            <p>To use this dashboard, please ensure:</p>
            <ul className="mt-2 space-y-1 text-left">
              <li>• Docker is installed and running</li>
              <li>• Docker socket is accessible</li>
              <li>• Proper permissions are configured</li>
            </ul>
          </div>
          <button
            onClick={fetchData}
            className="mt-6 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="min-h-screen bg-cover bg-center bg-fixed"
      style={{
        backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0.3)), url(${backgroundImage})`
      }}
    >
      {/* Demo Mode Banner */}
      {dockerStatus?.status === 'demo' && (
        <div className="bg-yellow-600 bg-opacity-90 text-white text-center py-2 px-4 text-sm">
          <span className="font-medium">🚧 Demo Mode</span> - Showing mock data since Docker is not available in this environment
        </div>
      )}
      
      <div className="flex min-h-screen">
        {/* Right Sidebar */}
        <div className="w-80 bg-gray-800 bg-opacity-90 backdrop-blur-sm p-6 overflow-y-auto">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-white mb-2">Docker Monitor</h1>
            <div className="text-gray-300">
              <p className="text-sm">Server: localhost</p>
              <p className="text-sm">Docker: {dockerStatus?.server_version}</p>
              {dockerStatus?.status === 'demo' && (
                <p className="text-xs text-yellow-400 mt-1">⚠️ Demo Mode - Mock Data</p>
              )}
            </div>
          </div>

          {/* Docker Status */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-white mb-4">Status</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between text-gray-300">
                <span>Running:</span>
                <span className="text-green-500">{dockerStatus?.containers_running || 0}</span>
              </div>
              <div className="flex justify-between text-gray-300">
                <span>Stopped:</span>
                <span className="text-red-500">{dockerStatus?.containers_stopped || 0}</span>
              </div>
              <div className="flex justify-between text-gray-300">
                <span>Images:</span>
                <span className="text-blue-500">{dockerStatus?.images || 0}</span>
              </div>
            </div>
          </div>

          {/* Running Containers */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-white mb-4">Running Containers</h2>
            <div className="space-y-3">
              {containers.filter(c => c.status === 'running').map((container) => (
                <div
                  key={container.id}
                  className="flex items-center space-x-3 p-3 bg-gray-700 bg-opacity-50 rounded-lg hover:bg-opacity-70 cursor-pointer transition-all"
                  onClick={() => handleContainerClick(container)}
                >
                  <span className="text-2xl">{getContainerIcon(container.image)}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate">{container.name}</p>
                    <p className="text-gray-400 text-sm truncate">{container.image}</p>
                  </div>
                  <div className={`w-2 h-2 rounded-full ${getStatusColor(container.status)}`}></div>
                </div>
              ))}
            </div>
          </div>

          {/* Stopped Containers */}
          {containers.filter(c => c.status !== 'running').length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-white mb-4">Stopped Containers</h2>
              <div className="space-y-3">
                {containers.filter(c => c.status !== 'running').map((container) => (
                  <div
                    key={container.id}
                    className="flex items-center space-x-3 p-3 bg-gray-700 bg-opacity-30 rounded-lg hover:bg-opacity-50 cursor-pointer transition-all"
                    onClick={() => handleContainerClick(container)}
                  >
                    <span className="text-2xl opacity-50">{getContainerIcon(container.image)}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-gray-300 font-medium truncate">{container.name}</p>
                      <p className="text-gray-500 text-sm truncate">{container.image}</p>
                    </div>
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(container.status)}`}></div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Main Content */}
        <div className="flex-1 p-8">
          <div className="mb-8">
            <h2 className="text-3xl font-bold text-white mb-2">Docker Images</h2>
            <p className="text-gray-300">Hover over an image to see details, click to manage</p>
          </div>

          {/* Images Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {images.map((image) => (
              <div
                key={`${image.id}-${image.tag}`}
                className="group relative bg-gray-800 bg-opacity-70 backdrop-blur-sm rounded-lg p-6 hover:bg-opacity-90 hover:scale-105 transition-all duration-300 cursor-pointer"
                onClick={() => {
                  // Handle image click - could show image details
                  console.log('Image clicked:', image);
                }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="text-4xl">{getContainerIcon(image.tag)}</div>
                  <div className="text-gray-400 text-sm">
                    {image.short_id.replace('sha256:', '').substring(0, 12)}
                  </div>
                </div>
                
                <h3 className="text-white font-semibold mb-2 truncate">{image.tag}</h3>
                
                <div className="space-y-1 text-sm text-gray-300">
                  <div className="flex justify-between">
                    <span>Size:</span>
                    <span>{formatBytes(image.size)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Created:</span>
                    <span>{new Date(image.created).toLocaleDateString()}</span>
                  </div>
                </div>

                {/* Hover Details */}
                <div className="absolute inset-x-0 bottom-0 bg-gray-900 bg-opacity-95 p-4 rounded-b-lg transform translate-y-full opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-300">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between text-gray-300">
                      <span>Architecture:</span>
                      <span>{image.architecture}</span>
                    </div>
                    <div className="flex justify-between text-gray-300">
                      <span>Virtual Size:</span>
                      <span>{formatBytes(image.virtual_size)}</span>
                    </div>
                    <div className="mt-3 pt-3 border-t border-gray-700">
                      <button className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors">
                        Manage Image
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Container Detail Modal */}
      {showDetailModal && selectedContainer && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-4xl w-full max-h-[90vh] overflow-y-auto m-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-white">
                {getContainerIcon(selectedContainer.image)} {selectedContainer.name}
              </h2>
              <button
                onClick={() => setShowDetailModal(false)}
                className="text-gray-400 hover:text-white text-2xl"
              >
                ×
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Container Info */}
              <div className="bg-gray-700 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-white mb-4">Container Info</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-300">Status:</span>
                    <span className={getStatusColor(selectedContainer.status)}>
                      {selectedContainer.status}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Image:</span>
                    <span className="text-white">{selectedContainer.image}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">ID:</span>
                    <span className="text-white font-mono">{selectedContainer.short_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Uptime:</span>
                    <span className="text-white">{formatUptime(selectedContainer.uptime)}</span>
                  </div>
                </div>
              </div>

              {/* Resource Usage */}
              <div className="bg-gray-700 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-white mb-4">Resource Usage</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-300">CPU:</span>
                    <span className="text-white">{containerStats.cpu_percent || 0}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Memory:</span>
                    <span className="text-white">
                      {formatBytes(containerStats.memory_usage || 0)} / {formatBytes(containerStats.memory_limit || 0)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Memory %:</span>
                    <span className="text-white">{containerStats.memory_percent || 0}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Network RX:</span>
                    <span className="text-white">{formatBytes(containerStats.network_rx || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300">Network TX:</span>
                    <span className="text-white">{formatBytes(containerStats.network_tx || 0)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Logs */}
            <div className="mt-6 bg-gray-700 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-4">Logs (Last 100 lines)</h3>
              <div className="bg-gray-900 rounded p-4 max-h-64 overflow-y-auto">
                <pre className="text-sm text-gray-300 whitespace-pre-wrap">
                  {containerLogs || 'No logs available'}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;