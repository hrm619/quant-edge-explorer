import { Component, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="my-2 border border-red-200 rounded bg-red-50 p-4">
          <p className="text-sm font-medium text-trust-untrusted mb-1">
            {this.props.fallbackMessage ?? "Something went wrong rendering this content"}
          </p>
          {this.state.error && (
            <pre className="text-xs font-mono text-neutral-600 bg-white rounded p-2 mt-2 overflow-x-auto">
              {this.state.error.message}
            </pre>
          )}
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
