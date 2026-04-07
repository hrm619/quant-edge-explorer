import { useServerHealth } from "@/hooks/useServerHealth";

export function ConnectionStatus() {
  const { isConnected } = useServerHealth();

  if (isConnected) return null;

  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-xs text-amber-800">
      Server unavailable — start with{" "}
      <code className="font-mono bg-amber-100 px-1 rounded">quant-edge serve</code>
    </div>
  );
}
