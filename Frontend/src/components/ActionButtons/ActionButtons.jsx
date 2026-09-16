import "./ActionButtons.css";

import { RefreshCw, Download, User } from "lucide-react";

import { useState, useCallback, useRef, useEffect } from "react";

import jsPDF from "jspdf";
import html2canvas from "html2canvas";

import { COLORS } from '../../constants/colorConstant';
import { supabase } from '../../services/supabaseClient';

const ActionButtons = ({
  isLoading,
  dashboardRef,
  onReanalyze,
  username,
  dashboardData,
  onProfileClick,
}) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const handleDownload = useCallback(async () => {
    if (isDownloading) return;

    const dashboard = dashboardRef?.current;

    if (!dashboard) {
      console.error("Dashboard not found");
      return;
    }

    let originalWidth = "";

    try {
      setIsDownloading(true);

      originalWidth = dashboard.style.width;

      dashboard.style.width = "720px";

      const canvas = await html2canvas(dashboard, {
        scale: 2,
        useCORS: true,
        backgroundColor: COLORS.background.main,
        width: 720,
        windowWidth: 720,
        logging: false,
      });

      dashboard.style.width = originalWidth;

      const imgData = canvas.toDataURL("image/png");

      const pdf = new jsPDF("p", "mm", "a4");

      const pdfWidth = pdf.internal.pageSize.getWidth();

      const pdfHeight = pdf.internal.pageSize.getHeight();

      const margin = 8;

      const usableWidth = pdfWidth - margin * 2;

      /* Header */

      pdf.setFont("helvetica", "bold");

      pdf.setFontSize(20);

      pdf.setTextColor(99, 102, 241);

      pdf.text("GitHub Analyzer Report", pdfWidth / 2, 18, {
        align: "center",
      });

      pdf.setFont("helvetica", "normal");

      pdf.setFontSize(10);

      pdf.setTextColor(120, 120, 120);

      pdf.text(
        `Generated on ${new Date().toLocaleString()}`,
        pdfWidth / 2,
        25,
        {
          align: "center",
        },
      );

      const topOffset = 35;

      const imgHeight = (canvas.height * usableWidth) / canvas.width;

      let heightLeft = imgHeight;

      let position = topOffset;

      pdf.addImage(imgData, "PNG", margin, position, usableWidth, imgHeight);

      heightLeft -= pdfHeight - topOffset;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;

        pdf.addPage();

        pdf.addImage(imgData, "PNG", margin, position, usableWidth, imgHeight);

        heightLeft -= pdfHeight;
      }

      /* Footer */

      const totalPages = pdf.internal.getNumberOfPages();

      for (let i = 1; i <= totalPages; i++) {
        pdf.setPage(i);

        pdf.setFontSize(8);

        pdf.setTextColor(140, 140, 140);

        pdf.text(`Page ${i} of ${totalPages}`, pdfWidth / 2, pdfHeight - 5, {
          align: "center",
        });
      }

      pdf.save(`${username || "github-user"}-analysis.pdf`);
    } catch (error) {
      console.error("PDF Download Error:", error);

      alert("Failed to generate PDF. Please try again.");
    } finally {
      if (dashboard) {
        dashboard.style.width = originalWidth;
      }

      if (isMountedRef.current) {
        setIsDownloading(false);
      }
    }
  }, [dashboardRef, isDownloading, username]);

  return (
    <>
      <div
        className={`action-buttons-card ${isLoading ? "buttons-disabled" : ""}`}
      >
        {/* Reanalyze */}
        <button
          className="reanalyze-btn"
          disabled={isLoading}
          onClick={onReanalyze}
        >
          <RefreshCw size={18} className={isLoading ? "spin-icon" : ""} />

          <span>
            {isLoading
              ? "Fetching Latest Insights..."
              : "Analyze This Profile Again"}
          </span>
        </button>

        {/* Download */}
        <button
          className="icon-btn"
          disabled={isLoading || isDownloading}
          onClick={handleDownload}
          title="Download Report"
        >
          <Download size={20} className={isDownloading ? "spin-icon" : ""} />
        </button>

        {/* Profile */}
        <button
          className="icon-btn profile-btn"
          disabled={isLoading}
          onClick={onProfileClick}
          title="Profile"
        >
          <User size={20} />
          <span style={{ marginLeft: '8px' }}>Profile</span>
        </button>
      </div>
    </>
  );
};

export default ActionButtons;
