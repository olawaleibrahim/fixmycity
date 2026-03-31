/** @type {import('next').NextConfig} */
const nextConfig = {
  // Leaflet needs this to avoid SSR issues with window
  transpilePackages: ["leaflet", "react-leaflet"],
};

module.exports = nextConfig;
