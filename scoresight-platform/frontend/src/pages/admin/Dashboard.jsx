import { useEffect, useState } from "react";
import Shell from "../../components/Shell.jsx";
import { Card, CardHead, Pad, Stat, Loading, Notice } from "../../components/ui.jsx";
import { Donut, Bars } from "../../components/charts.jsx";
import { api } from "../../lib/api.js";

export default function AdminDashboard() {
  const [a, setA] = useState(undefined);
  useEffect(() => { api.monitoring().then(setA).catch(() => setA(null)); }, []);
  if (a === undefined) return <Shell title="Giám sát mô hình" crumb="Cổng Quản trị & Kiểm toán"><Loading /></Shell>;

  const flow = [
    { label: "Luồng Xanh", value: a.flow_distribution.green, color: "var(--green)" },
    { label: "Luồng Vàng", value: a.flow_distribution.yellow, color: "var(--amber)" },
    { label: "Luồng Đỏ", value: a.flow_distribution.red, color: "var(--red)" },
  ];
  const tiers = Object.entries(a.tier_distribution).map(([k, v]) => ({ label: `Hạng ${k}`, value: v }));
  const dsr = [
    { label: "Mỏng (thin)", value: a.dsr_distribution.thin },
    { label: "Trung bình (semi)", value: a.dsr_distribution.semi },
    { label: "Dày (thick)", value: a.dsr_distribution.thick },
  ];
  const pdOrder = ["Rất thấp", "Thấp", "Trung bình - thấp", "Trung bình", "Cao"];
  const pd = pdOrder.filter((k) => a.pd_distribution[k] != null).map((k) => ({ label: k, value: a.pd_distribution[k] }));

  return (
    <Shell title="Giám sát mô hình" crumb="Cổng Quản trị & Kiểm toán">
      <div className="cols cols-4 fade fade-1">
        <Stat k="Hồ sơ đã xử lý" value={a.applications_processed} sub="Tổng danh mục mẫu" />
        <Stat k="Tỷ lệ phê duyệt nhanh" value={a.approval_rate} unit="%" sub="Luồng Xanh / tổng" />
        <Stat k="Điểm trung bình" value={a.avg_score} sub="Thang 300–850" />
        <Stat k="Nợ xấu trong nhóm duyệt" value={a.bad_rate_in_approve} unit="%" sub="So với ~9% nền" />
      </div>

      <div className="cols cols-4 fade fade-2" style={{ marginTop: 18 }}>
        <Stat k="Tiết kiệm thời gian (TB)" value={a.avg_tat_saving} unit="%" sub="Ước tính theo luồng" />
        <Stat k="Tỷ lệ ghi đè thủ công" value={a.manual_override_rate} unit="%" sub="Giám sát quản trị" />
        <Stat k="Chất lượng phủ dữ liệu" value={a.data_coverage_quality} unit="%" sub="Trung bình DSR" />
        <Stat k="Trôi dạt mô hình (PSI)" value={a.model_drift_psi} sub={a.model_drift_psi < 0.1 ? "Ổn định (<0.1)" : "Cần theo dõi"} />
      </div>

      <div className="cols cols-2-1 fade fade-3" style={{ marginTop: 18 }}>
        <Card>
          <CardHead eyebrow="Phân bổ quyết định" title="Luồng Xanh / Vàng / Đỏ" />
          <Pad>
            <Donut data={flow} centerLabel={a.applications_processed} centerSub="hồ sơ" />
          </Pad>
        </Card>
        <Card>
          <CardHead eyebrow="Sức khỏe danh mục" title="Chỉ số chính" />
          <Pad>
            <Notice kind="ok">Tỷ lệ nợ xấu trong nhóm được duyệt chỉ <b>{a.bad_rate_in_approve}%</b> — thấp hơn nhiều so với mức nền của danh mục.</Notice>
            <div className="kv" style={{ marginTop: 8 }}><span className="k">Xu hướng NPL</span><span className="v">{a.npl_trend}</span></div>
            <div className="kv"><span className="k">PSI (drift)</span><span className="v">{a.model_drift_psi}</span></div>
            <div className="kv"><span className="k">Phủ dữ liệu TB</span><span className="v">{a.data_coverage_quality}%</span></div>
          </Pad>
        </Card>
      </div>

      <div className="cols cols-3 fade fade-4" style={{ marginTop: 18 }}>
        <Card><CardHead eyebrow="Phân bổ" title="Hạng rủi ro" /><Pad><Bars data={tiers} color="#2b6fb5" /></Pad></Card>
        <Card><CardHead eyebrow="Phân bổ" title="Độ dày dữ liệu (DSR)" /><Pad><Bars data={dsr} color="var(--shb-orange)" /></Pad></Card>
        <Card><CardHead eyebrow="Phân bổ" title="Dải xác suất vỡ nợ" /><Pad><Bars data={pd} color="var(--navy-3)" /></Pad></Card>
      </div>
    </Shell>
  );
}
