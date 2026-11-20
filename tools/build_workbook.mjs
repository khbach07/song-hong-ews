import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [payload, outDir, previewDir] = process.argv.slice(2);
if (!payload || !outDir) throw new Error("Usage: node build_workbook.mjs workbook_input.json OUT_DIR [PREVIEW_DIR]");
const d = JSON.parse(await fs.readFile(payload, "utf8"));
const wb = Workbook.create();
const specs = [
    ["dashboard", "06_Dashboard", "Danh mục cảnh báo theo tháng"],
    ["alerts", "05_EWS_Alerts", "Mẫu khoản vay và hành động"],
    ["backtest", "07_Backtesting", "Kiểm định ngoài thời gian · 30+"],
    ["score", "04_Model_Scoring", "Mô hình, xác suất và ngưỡng"],
    ["indicators", "03_Risk_Indicators", "Chỉ báo hành vi tại snapshot"],
    ["profile", "02_Customer_Profile", "Đặc trưng hồ sơ sau làm sạch"],
    ["raw", "01_Raw_Data", "Mẫu DPD quan sát đến thời điểm chấm điểm"],
    ["instructions", "00_Instructions", "Sông Hồng · Hướng dẫn sử dụng"],
];
const sheets = Object.fromEntries(specs.map(([key, name, title]) => {
    const sh = wb.worksheets.add(name);
    sh.showGridLines = false;
    sh.getRange("A2").values = [[title]];
    sh.getRange("A2").format.font = { bold: true, size: 18, color: "#15364C" };
    sh.getRange("A2:H2").format.rowHeight = 27;
    return [key, sh];
}));

function note(sh, row, text) {
    const cell = sh.getCell(row - 1, 0);
    cell.values = [[text]];
    cell.format.font = { italic: true, color: "#496779", size: 10 };
}

function block(sh, row, headers, data, widths = [], percentages = []) {
    const header = sh.getRangeByIndexes(row - 1, 0, 1, headers.length);
    header.values = [headers];
    header.format.fill = "#193B54";
    header.format.font = { bold: true, color: "#FFFFFF", size: 10 };
    header.format.rowHeight = 24;
    if (data.length) {
        const body = sh.getRangeByIndexes(row, 0, data.length, headers.length);
        body.values = data;
        body.format.font = { name: "Aptos", size: 10, color: "#203749" };
        body.format.rowHeight = 17;
        for (const i of percentages) sh.getRangeByIndexes(row, i, data.length, 1).setNumberFormat("0.000%");
    }
    widths.forEach((width, i) => {
        sh.getRangeByIndexes(row - 1, i, data.length + 1, 1).format.columnWidthPx = width;
    });
}

const levels = ["Existing 30+", "Red", "Orange", "Yellow", "Green"];
const fills = ["#ECE4F8", "#FBDDDD", "#FBE7D9", "#FDF2CE", "#DEF3E8"];
const total = d.summary.snapshot_total;
const dashboard = sheets.dashboard;
note(dashboard, 3, `Snapshot lịch sử ${d.summary.snapshot_month}  ·  Toàn bộ danh mục  ·  Mục tiêu 30+ trong 3 tháng`);
block(dashboard, 5, ["Cấp", "Khoản vay", "Tỷ trọng danh mục"],
    levels.map(level => [level, d.summary.snapshot_alerts[level] ?? 0, null]), [160, 115, 150], [2]);
dashboard.getRange("C6:C10").formulas = levels.map((_, i) => [`=B${i + 6}/$B$11`]);
dashboard.getRange("A11").values = [["Tổng"]];
dashboard.getRange("B11:C11").formulas = [["=SUM(B6:B10)", "=SUM(C6:C10)"]];
dashboard.getRange("C11").setNumberFormat("0.000%");
levels.forEach((_, i) => { dashboard.getRange(`A${i + 6}`).format.fill = fills[i]; });
const distribution = dashboard.charts.add("bar", dashboard.getRange("A5:B10"));
distribution.title = "Số khoản vay theo cấp";
distribution.setPosition("E5", "M17");
note(dashboard, 18, `Danh mục đầy đủ gồm ${total.toLocaleString("vi-VN")} khoản. Mở dashboard.html hoặc scored.csv để xem tất cả.`);
note(dashboard, 19, "Existing 30+ là luồng xử lý quá hạn hiện hữu, có quy trình ưu tiên riêng.");

const score = sheets.score;
note(score, 3, "Ngưỡng mẫu được xác định từ validation. File này chứa PD xuất từ Python.");
block(score, 5, ["Cấp", "Ngưỡng PD", "Công suất giả định", "Tỷ trọng validation"],
    d.thresholds.data, [210, 132, 150, 158], [1, 2, 3]);
note(score, 11, "So sánh mô hình tại validation · 30+");
block(score, 12, ["Mô hình", "Snapshot", "Sự kiện", "Tỷ lệ sự kiện", "AP", "ROC-AUC", "Brier", "PD trung bình"],
    d.comparison_30.data, [], [3, 4, 5, 6, 7]);
note(score, 20, "So sánh mô hình tại validation · 90+");
block(score, 21, ["Mô hình", "Snapshot", "Sự kiện", "Tỷ lệ sự kiện", "AP", "ROC-AUC", "Brier", "PD trung bình"],
    d.comparison_90.data, [225, 120, 150, 130, 100, 110, 100, 140], [3, 4, 5, 6, 7]);

const alerts = sheets.alerts;
note(alerts, 3, "Tối đa 80 khoản mỗi cấp. Cấp Excel tính từ PD của Python và ngưỡng ở 04_Model_Scoring.");
const alertFields = ["app_id", "cohort", "mob", "dpd_current", "pd_3m", "alert_level", "reason", "action"];
const alertRows = d.alerts.data.map(row => alertFields.map(field => row[d.alerts.columns.indexOf(field)]));
block(alerts, 5, ["Mã khoản vay", "Cohort", "MOB", "DPD", "PD 30+/3M", "Cấp Excel", "Tín hiệu quan sát", "Hành động tại ngưỡng gốc"],
    alertRows, [135, 95, 70, 75, 115, 135, 490, 500], [4]);
const thresholds = "'04_Model_Scoring'";
alerts.getRange(`F6:F${5 + alertRows.length}`).formulas = alertRows.map((_, i) => {
    const r = i + 6;
    return [`=IF(D${r}>=30,"Existing 30+",IF(E${r}="","",IF(E${r}>=${thresholds}!$B$9,"Red",IF(E${r}>=${thresholds}!$B$8,"Orange",IF(E${r}>=${thresholds}!$B$7,"Yellow","Green")))))`];
});
alerts.freezePanes.freezeRows(5);

const backtest = sheets.backtest;
note(backtest, 3, "Chỉ dùng snapshot đủ 3 tháng theo dõi. PD bình quân và tỷ lệ thực tế dùng cùng mẫu.");
const backRows = d.backtest_monthly.data.map(([month, n, events, , pd]) => [month, n, events, null, pd]);
block(backtest, 5, ["Tháng", "Snapshot", "Sự kiện", "Tỷ lệ thực tế", "PD bình quân"], backRows,
    [135, 110, 110, 150, 140], [3, 4]);
const backEnd = backRows.length + 5;
backtest.getRange(`D6:D${backEnd}`).formulas = backRows.map((_, i) => [`=C${i + 6}/B${i + 6}`]);
const trend = backtest.charts.add("line", [
    backtest.getRange(`A5:A${backEnd}`),
    backtest.getRange(`D5:D${backEnd}`),
    backtest.getRange(`E5:E${backEnd}`),
]);
trend.title = "PD bình quân và tỷ lệ quá hạn thực tế";
trend.yAxis = { numberFormatCode: "0.0%", numberFormatSourceLinked: false };
trend.setPosition("G5", "Q21");
const m = d.summary.models["30"].oot;
block(backtest, 23, ["Chỉ tiêu", "Giá trị"], [
    ["Average precision", m.average_precision], ["ROC-AUC", m.roc_auc],
    ["Brier", m.brier], ["Tỷ lệ sự kiện", m.event_rate], ["PD bình quân", m.mean_pd],
], [], [1]);

for (const [sheetKey, dataKey, label] of [
    ["indicators", "features", "Nguồn tính chỉ báo: song_hong_perf_monthly.csv"],
    ["profile", "profiles", "Nguồn: song_hong_dev_2023.csv và song_hong_oot_2024H1.csv"],
    ["raw", "raw", "Nguồn: song_hong_perf_monthly.csv. DPD sau MOB chấm điểm được ẩn khỏi bảng mẫu."],
]) {
    const sh = sheets[sheetKey];
    note(sh, 3, label);
    const { columns, data } = d[dataKey];
    block(sh, 5, columns, data.map(row => row.map(value =>
        typeof value === "string" && /^\d{4}-\d{2}-\d{2}T00:00:00/.test(value) ? value.slice(0, 10) : value
    )), columns.map(x => Math.max(105, x.length * 8 + 28)));
    if (sheetKey === "indicators" && data.length) {
        sh.getRange(`E6:E${5 + data.length}`).setNumberFormat("0.00");
    }
    sh.freezePanes.freezeRows(5);
}
block(sheets.raw, 409, d.inventory.columns, d.inventory.data, [160, 120, 120, 130, 130]);

const instructions = sheets.instructions;
block(instructions, 5, ["Khi cần", "Cách dùng"], [
    ["Giám sát đầy đủ", "Mở dashboard.html để tra mã khoản vay, lọc mức và cohort. Scored.csv có toàn bộ snapshot."],
    ["Xem cảnh báo mẫu", "05_EWS_Alerts hiển thị tối đa 80 khoản mỗi cấp và tính lại cấp khi đổi ngưỡng."],
    ["Xem kết quả gốc", "06_Dashboard và cột hành động dùng các ngưỡng chính thức của lượt chạy Python."],
    ["Kiểm định", "07_Backtesting dùng OOT, mỗi dòng là một tháng đánh giá với nhãn đủ quan sát."],
    ["Chấm điểm", "Python tính xác suất 30+ và 90+. Existing 30+ được chuyển sang luồng xử lý quá hạn."],
    ["Tính lại", "Hướng dẫn chạy, sơ đồ nghiệp vụ và quy ước dữ liệu nằm trong README.md và docs."],
], [170, 760]);
wb.recalculate();
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await fs.mkdir(outDir, { recursive: true });
await xlsx.save(path.join(outDir, "EWS_Excel.xlsx"));
if (previewDir) {
    await fs.mkdir(previewDir, { recursive: true });
    for (const [key, name] of specs) {
        const range = key === "dashboard" ? "A1:M20" : key === "backtest" ? "A1:Q22" : "A1:H10";
        const image = await wb.render({ sheetName: name, range, scale: 1, format: "png" });
        await fs.writeFile(path.join(previewDir, key + ".png"), new Uint8Array(await image.arrayBuffer()));
    }
}
