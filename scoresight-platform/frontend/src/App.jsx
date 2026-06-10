import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./lib/auth.jsx";

import Login from "./pages/Login.jsx";
import CustomerDashboard from "./pages/customer/Dashboard.jsx";
import NewApplication from "./pages/customer/NewApplication.jsx";
import CustomerStatus from "./pages/customer/Status.jsx";
import BankCases from "./pages/bank/Cases.jsx";
import QuickScore from "./pages/bank/QuickScore.jsx";
import CaseDetail from "./pages/bank/CaseDetail.jsx";
import AdminDashboard from "./pages/admin/Dashboard.jsx";
import AdminCases from "./pages/admin/Cases.jsx";
import CaseAudit from "./pages/admin/CaseAudit.jsx";
import RuleEngine from "./pages/admin/RuleEngine.jsx";
import Governance from "./pages/admin/Governance.jsx";

function Protected({ roles, children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={user.home} replace />;
  return children;
}

export default function App() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to={user.home} replace /> : <Login />} />

      {/* Customer */}
      <Route path="/customer/dashboard" element={<Protected roles={["customer"]}><CustomerDashboard /></Protected>} />
      <Route path="/customer/application" element={<Protected roles={["customer"]}><NewApplication /></Protected>} />
      <Route path="/customer/status" element={<Protected roles={["customer"]}><CustomerStatus /></Protected>} />

      {/* Bank user (admin may also view) */}
      <Route path="/bank/cases" element={<Protected roles={["bank_user", "admin"]}><BankCases /></Protected>} />
      <Route path="/bank/cases/:cid" element={<Protected roles={["bank_user", "admin"]}><CaseDetail /></Protected>} />
      <Route path="/bank/quick-score" element={<Protected roles={["bank_user", "admin"]}><QuickScore /></Protected>} />

      {/* Admin */}
      <Route path="/admin/dashboard" element={<Protected roles={["admin"]}><AdminDashboard /></Protected>} />
      <Route path="/admin/cases" element={<Protected roles={["admin"]}><AdminCases /></Protected>} />
      <Route path="/admin/cases/:cid" element={<Protected roles={["admin"]}><CaseAudit /></Protected>} />
      <Route path="/admin/rule-engine" element={<Protected roles={["admin"]}><RuleEngine /></Protected>} />
      <Route path="/admin/governance" element={<Protected roles={["admin"]}><Governance /></Protected>} />

      <Route path="*" element={<Navigate to={user ? user.home : "/login"} replace />} />
    </Routes>
  );
}
