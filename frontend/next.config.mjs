/** @type {import('next').NextConfig} */
const nextConfig = {
  // The Vercel adapter is identified by NEXT_ADAPTER_PATH. In Next 16.3 it
  // omits the root NFT trace file, but standalone still tries to consume it.
  // Keep standalone for Docker/self-hosting, where no build adapter is used.
  ...(process.env.NEXT_ADAPTER_PATH ? {} : { output: "standalone" }),
};

export default nextConfig;
