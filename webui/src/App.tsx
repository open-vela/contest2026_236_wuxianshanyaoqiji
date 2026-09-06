import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ChatPage } from "@/pages/Chat";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ChatPage />} />
      </Routes>
    </Router>
  );
}
