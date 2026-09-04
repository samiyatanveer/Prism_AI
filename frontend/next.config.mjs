/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required by the production Docker stage, which runs the generated server.
  output: "standalone",
};

export default nextConfig;
