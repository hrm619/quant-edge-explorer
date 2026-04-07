import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ChatRoute } from "@/routes/ChatRoute";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatRoute />} />
        <Route path="/c/:conversationId" element={<ChatRoute />} />
        <Route
          path="/artifacts"
          element={
            <div className="flex items-center justify-center h-screen text-neutral-400">
              Artifact browser — Phase 3
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
