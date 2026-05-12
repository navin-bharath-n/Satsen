import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ManualFireUpload from "./pages/ManualFireUpload";
import ControlCenter from "./pages/ControlCenter";
import GlobePage from "./pages/GlobePage";
import EmergencyControl from "./pages/EmergencyControl";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/manual-upload" element={<ManualFireUpload />} />
        <Route path="/control-center" element={<ControlCenter />} />
        <Route path="/globe" element={<GlobePage />} />
        <Route path="/Emergency" element={<EmergencyControl />} />
      </Routes>
    </Router>
  );
}
export default App;
