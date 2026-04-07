import { useState } from "react";
import { Flag } from "lucide-react";
import { updateArtifactFlag } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";

interface QualityFlagMenuProps {
  artifactId: string;
  currentFlag: string;
}

const FLAGS = [
  { value: "unflagged", label: "Unflagged", color: "text-neutral-400" },
  { value: "trusted", label: "Trusted", color: "text-trust-trusted" },
  { value: "untrusted", label: "Untrusted", color: "text-trust-untrusted" },
] as const;

export function QualityFlagMenu({ artifactId, currentFlag }: QualityFlagMenuProps) {
  const [flag, setFlag] = useState(currentFlag);

  async function handleSelect(value: string) {
    setFlag(value);
    try {
      await updateArtifactFlag(artifactId, value);
    } catch {
      setFlag(currentFlag); // Revert on failure
    }
  }

  const current = FLAGS.find((f) => f.value === flag) ?? FLAGS[0];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className={cn("p-1 rounded hover:bg-neutral-200", current.color)}
          title={`Quality: ${current.label}`}
        >
          <Flag className="h-3.5 w-3.5" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {FLAGS.map((f) => (
          <DropdownMenuItem
            key={f.value}
            onClick={() => handleSelect(f.value)}
            className={cn(f.value === flag && "bg-surface-muted")}
          >
            <Flag className={cn("h-3.5 w-3.5 mr-2", f.color)} />
            {f.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
