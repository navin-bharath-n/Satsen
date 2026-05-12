import { Navigate } from "react-router-dom";

export default function AdminGuard({ children }) {
  const isAdmin = localStorage.getItem("role") === "admin";

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return children;
}
