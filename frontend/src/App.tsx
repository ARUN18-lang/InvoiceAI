import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ChatPage } from "@/pages/ChatPage";
import { InvoiceDetailPage } from "@/pages/InvoiceDetailPage";
import { InvoicesPage } from "@/pages/InvoicesPage";
import { OverviewPage } from "@/pages/OverviewPage";
import { ReportsPage } from "@/pages/ReportsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Navigate to="/invoices" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/invoices" element={<InvoicesPage />} />
        <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/reports" element={<ReportsPage />} />
      </Route>
    </Routes>
  );
}
