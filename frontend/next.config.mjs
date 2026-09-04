/** @type {import('next').NextConfig} */
const nextConfig = {
  // Docker uses the minimal standalone server, but Vercel deploys Next.js with
  // its own adapter. Next 16.3's adapter omits the root NFT trace file while
  // standalone still attempts to consume it, causing the post-build ENOENT.
  // Vercel never consumes our standalone output, so keep it for Docker only.
  ...(process.env.VERCEL ? {} : { output: "standalone" }),
};

export default nextConfig;
