/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@treemap/types', '@treemap/api-client'],
};

export default nextConfig;
