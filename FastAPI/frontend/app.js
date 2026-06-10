const API_BASE = new URLSearchParams(window.location.search).get("api") || "http://3.229.176.126:8000/api";
const DEMO_DOCUMENT_ID = "demo-document";

const state = {
  selectedFile: null,
  documentId: DEMO_DOCUMENT_ID,
  completedChecks: new Set(),
  openedChecks: new Set(),
  uploadResult: null,
  analysis: null,
  report: null,
  authToken: localStorage.getItem("access_token"),
  authUser: JSON.parse(localStorage.getItem("auth_user") || "null"),
};

const elements = {
  fileInput: document.querySelector("#contract-file"),
  fileName: document.querySelector("#file-name"),
  fileMeta: document.querySelector("#file-meta"),
  documentType: document.querySelector("#document-type"),
  analyzeButton: document.querySelector("#analyze-button"),
  status: document.querySelector("#connection-status"),
  headerScore: document.querySelector("#header-score"),
  headerScoreLabel: document.querySelector("#header-score-label"),
  riskScore: document.querySelector("#risk-score"),
  riskFormula: document.querySelector("#risk-formula"),
  riskLevelPill: document.querySelector("#risk-level-pill"),
  completedCount: document.querySelector("#completed-count"),
  checklistGroups: document.querySelector("#checklist-groups"),
  recommendedActions: document.querySelector("#recommended-actions"),
  specialTerms: document.querySelector("#special-terms"),
  documentViewer: document.querySelector("#document-viewer"),
  downloadReport: document.querySelector("#download-report"),
  fieldSummaryList: document.querySelector(".info-list"),
  contractType: document.querySelector("#contract-type"),
  deposit: document.querySelector("#deposit"),
  leasePeriod: document.querySelector("#lease-period"),
  fixedDate: document.querySelector("#fixed-date"),
  moveIn: document.querySelector("#move-in"),
  seniorRights: document.querySelector("#senior-rights"),
  authForms: document.querySelector("#auth-forms"),
  authUser: document.querySelector("#auth-user"),
  authUserName: document.querySelector("#auth-user-name"),
  authMessage: document.querySelector("#auth-message"),
  loginEmail: document.querySelector("#login-email"),
  loginPassword: document.querySelector("#login-password"),
  loginButton: document.querySelector("#login-button"),
  signupName: document.querySelector("#signup-name"),
  signupEmail: document.querySelector("#signup-email"),
  signupPassword: document.querySelector("#signup-password"),
  signupButton: document.querySelector("#signup-button"),
  logoutButton: document.querySelector("#logout-button"),
};

const SUMMARY_FIELD_LABELS = {
  contract_type: "계약 유형",
  address: "소재지",
  land_area: "토지",
  building_info: "건물",
  lease_area: "임대할 부분",
  deposit_amount: "보증금",
  monthly_rent: "월 차임",
  sale_price: "매매대금",
  contract_payment: "계약금",
  intermediate_payment: "중도금",
  balance_payment: "잔금",
  lease_period: "임대차 기간",
  lease_start_date: "시작일",
  lease_end_date: "종료일",
  ownership_transfer_date: "소유권 이전일",
  landlord_name: "임대인",
  tenant_name: "임차인",
  seller_name: "매도인",
  buyer_name: "매수인",
  confirmed_date_status: "확정일자",
  move_in_report_status: "전입신고",
  priority_rights: "선순위 권리",
  special_terms: "특약",
};

const SUMMARY_FIELDS_BY_TYPE = {
  jeonse: [
    "contract_type",
    "address",
    "land_area",
    "building_info",
    "lease_area",
    "deposit_amount",
    "contract_payment",
    "balance_payment",
    "lease_period",
    "confirmed_date_status",
    "move_in_report_status",
    "priority_rights",
  ],
  monthly_rent: [
    "contract_type",
    "address",
    "land_area",
    "building_info",
    "lease_area",
    "deposit_amount",
    "monthly_rent",
    "contract_payment",
    "balance_payment",
    "lease_period",
    "confirmed_date_status",
    "move_in_report_status",
  ],
  mixed_rent: [
    "contract_type",
    "address",
    "land_area",
    "building_info",
    "lease_area",
    "deposit_amount",
    "monthly_rent",
    "contract_payment",
    "balance_payment",
    "lease_period",
    "priority_rights",
  ],
  sale: [
    "contract_type",
    "address",
    "land_area",
    "building_info",
    "lease_area",
    "sale_price",
    "contract_payment",
    "intermediate_payment",
    "balance_payment",
    "ownership_transfer_date",
  ],
  unknown: [
    "contract_type",
    "address",
    "land_area",
    "building_info",
    "lease_area",
    "deposit_amount",
    "monthly_rent",
    "sale_price",
    "lease_period",
  ],
};

const fallbackReport = {
  document_id: DEMO_DOCUMENT_ID,
  report_id: "report-demo-document",
  summary: "계약서 특약과 보증금 반환 조건에서 표준 계약서와 다른 위험 문구가 확인되었습니다.",
  risk_overview: "계약서 내 위험 문구와 확인 필요 항목을 기준으로 참고 지표를 산출했습니다.",
  risk_score: {
    base_score: 20,
    special_terms_delta: 12,
    checklist_reduction: 0,
    final_score: 32,
    risk_level: "caution",
    formula_version: "mvp-2026-06-09",
  },
  differences: [
    {
      category: "특약",
      original_text: "퇴거 시 일체의 수선비를 임차인이 부담한다",
      standard_text: "통상 사용으로 인한 마모를 제외한 수선 범위를 명확히 정한다",
      risk_level: "high",
      highlight_color: "red",
      locations: [],
      special_term_explanation:
        "원상복구 특약은 수선비 부담 범위가 과도하면 임차인에게 예상 밖의 비용을 전가할 수 있습니다.",
      risk_score_delta: 8,
    },
    {
      category: "보증금 반환",
      original_text: "임대인의 사정에 따라 반환일을 조정할 수 있다",
      standard_text: "임대차 종료와 동시에 보증금을 반환한다",
      risk_level: "medium",
      highlight_color: "orange",
      locations: [],
      special_term_explanation:
        "보증금 반환 시점이 모호하면 퇴거 후 반환 지연이나 공제 분쟁이 생길 수 있습니다.",
      risk_score_delta: 4,
    },
  ],
  recommended_actions: [
    "특약의 수선비 부담 범위와 한도를 구체적으로 수정하세요.",
    "보증금 반환일을 계약 종료일 또는 명도일과 명확하게 연결하세요.",
    "등기부등본, 건축물대장, 보증보험 가능 여부를 확인해 위험 점수를 낮추세요.",
  ],
  safety_checklist: [],
};

const fallbackChecklist = [
  {
    stage: "before_contract",
    title: "계약 전 확인",
    items: [
      checkItem(
        "registry_owner_check",
        "등기부등본 소유자 확인",
        "임대인과 등기상 소유자가 일치하는지 확인합니다.",
        6,
        "인터넷등기소에서 확인",
        "https://www.iros.go.kr",
      ),
      checkItem(
        "building_register_check",
        "건축물대장 확인",
        "주소, 용도, 위반건축물 여부를 확인합니다.",
        5,
        "정부24에서 확인",
        "https://m.gov.kr/mw/AA020InfoCappView.do?CappBizCD=15000000098&HighCtgCD=A09005&tp_seq=01",
      ),
      checkItem(
        "market_price_check",
        "실거래가와 시세 확인",
        "보증금이 주변 시세 대비 과도하지 않은지 확인합니다.",
        4,
        "실거래가 공개시스템에서 확인",
        "https://rt.molit.go.kr",
      ),
      checkItem(
        "guarantee_insurance_check",
        "전세보증금 반환보증 확인",
        "HUG 등에서 보증보험 가입 가능 여부를 확인합니다.",
        7,
        "HUG에서 확인",
        "https://www.khug.or.kr/hug/web/ig/dr/igdr000001.jsp",
      ),
    ],
  },
  {
    stage: "contract_day",
    title: "계약 당일 확인",
    items: [
      checkItem("owner_identity_check", "임대인 신분 확인", "신분증, 위임장, 인감증명서를 확인합니다.", 6),
      checkItem("deposit_account_owner_check", "입금 계좌 명의 확인", "계약금과 잔금 계좌가 임대인 명의인지 확인합니다.", 5),
      checkItem(
        "broker_registration_check",
        "중개사 등록 여부 확인",
        "공인중개사 등록번호와 사무소 정보를 확인합니다.",
        3,
        "국가공간정보포털에서 확인",
        "https://www.nsdi.go.kr",
      ),
    ],
  },
  {
    stage: "after_contract",
    title: "계약 후 진행",
    items: [
      checkItem(
        "move_in_report_check",
        "전입신고",
        "입주 즉시 전입신고를 진행합니다.",
        6,
        "정부24에서 전입신고",
        "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000016&HighCtgCD=A01010",
      ),
      checkItem("fixed_date_check", "확정일자", "계약서에 확정일자를 받습니다.", 6, "정부24에서 확인", "https://www.gov.kr"),
      checkItem("document_archive_check", "계약서와 영수증 보관", "계약서와 입금 영수증을 안전하게 보관합니다.", 2),
    ],
  },
];

function checkItem(id, label, description, points, actionLabel, url) {
  return {
    id,
    label,
    description,
    why_it_matters: description,
    priority: points >= 5 ? "high" : "medium",
    status: "unchecked",
    risk_reduction_points: points,
    external_action:
      actionLabel && url
        ? {
            label: actionLabel,
            url,
            type: "external_link",
            opens_in_new_window: true,
            completion_hint: "확인 페이지에서 내용을 대조한 뒤 완료 처리합니다.",
          }
        : null,
  };
}


function isLoggedIn() {
  return Boolean(state.authToken && state.authUser);
}

function setAuthMessage(message, type = "") {
  if (!elements.authMessage) return;
  elements.authMessage.textContent = message;
  elements.authMessage.className = `auth-message ${type}`.trim();
}

function saveAuthSession(data) {
  state.authToken = data.access_token;
  state.authUser = data.user;
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("auth_user", JSON.stringify(data.user));
  renderAuth();
}

function clearAuthSession() {
  state.authToken = null;
  state.authUser = null;
  localStorage.removeItem("access_token");
  localStorage.removeItem("auth_user");
  renderAuth();
}

function renderAuth() {
  if (!elements.authForms || !elements.authUser) return;

  if (isLoggedIn()) {
    elements.authForms.classList.add("hidden");
    elements.authUser.classList.remove("hidden");
    elements.authUserName.textContent = state.authUser.name || state.authUser.email || "사용자";
    setAuthMessage("로그인 완료", "success");
    return;
  }

  elements.authForms.classList.remove("hidden");
  elements.authUser.classList.add("hidden");
  setAuthMessage("로그인 후 계약서 분석을 이용할 수 있습니다.");
}

async function requestAuth(path, payload) {
  const response = await fetch(`${API_BASE}/auth/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "인증 요청에 실패했습니다.");
  }

  return data;
}

async function handleLogin() {
  const email = elements.loginEmail.value.trim();
  const password = elements.loginPassword.value;

  if (!email || !password) {
    setAuthMessage("이메일과 비밀번호를 입력하세요.", "error");
    return;
  }

  try {
    setAuthMessage("로그인 중입니다.");
    const data = await requestAuth("login", { email, password });
    saveAuthSession(data);
  } catch (error) {
    setAuthMessage(error.message, "error");
  }
}

async function handleSignup() {
  const name = elements.signupName.value.trim();
  const email = elements.signupEmail.value.trim();
  const password = elements.signupPassword.value;

  if (!name || !email || !password) {
    setAuthMessage("이름, 이메일, 비밀번호를 모두 입력하세요.", "error");
    return;
  }

  try {
    setAuthMessage("회원가입 중입니다.");
    const data = await requestAuth("signup", { name, email, password });
    saveAuthSession(data);
  } catch (error) {
    setAuthMessage(error.message, "error");
  }
}

function buildReportUrl(documentId) {
  const url = new URL(`${API_BASE}/reports/${documentId}`);
  state.completedChecks.forEach((id) => url.searchParams.append("completed_checks", id));
  return url.toString();
}

async function fetchReport(documentId = state.documentId) {
  try {
    setStatus("리포트 데이터를 불러오는 중");
    const response = await fetch(buildReportUrl(documentId));
    if (!response.ok) {
      throw new Error(`report api ${response.status}`);
    }
    const report = await response.json();
    state.report = normalizeReport(report);
    setStatus("backend 리포트 연결 완료");
  } catch (error) {
    state.report = normalizeReport(applyFallbackScore());
    setStatus("backend 연결 전이라 demo 데이터 표시 중");
  }
  render();
}

async function uploadSelectedFile() {
  if (!isLoggedIn()) {
    setStatus("로그인 후 계약서 분석을 이용할 수 있습니다.");
    setAuthMessage("먼저 로그인 또는 회원가입을 진행하세요.", "error");
    return;
  }

  if (!state.selectedFile) {
    state.documentId = DEMO_DOCUMENT_ID;
    await fetchReport(DEMO_DOCUMENT_ID);
    return;
  }

  const body = new FormData();
  body.append("file", state.selectedFile);
  body.append("source", state.selectedFile.type === "application/pdf" ? "pdf" : "mobile_scan");
  body.append("document_type", elements.documentType?.value || "unknown");

  try {
    setStatus("OCR 업로드 분석 중");
    elements.analyzeButton.disabled = true;
    const response = await fetch(`${API_BASE}/documents/upload`, {
      method: "POST",
      body,
    });
    if (!response.ok) {
      throw new Error(`upload api ${response.status}`);
    }
    const uploadResult = await response.json();
    state.uploadResult = uploadResult;
    state.documentId = uploadResult.document_id || DEMO_DOCUMENT_ID;
    setStatus("CLOVA 위험 조항 분석 중");
    state.analysis = await runAnalysis(state.documentId);
    setStatus("CLOVA 위험 조항 분석 완료");
    await fetchReport(state.documentId);
  } catch (error) {
    state.documentId = DEMO_DOCUMENT_ID;
    setStatus("실시간 OCR 실패, 발표용 demo 리포트로 전환");
    await fetchReport(DEMO_DOCUMENT_ID);
  } finally {
    elements.analyzeButton.disabled = false;
  }
}

async function runAnalysis(documentId) {
  const response = await fetch(`${API_BASE}/analysis/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      document_id: documentId,
      standard_contract_type: "jeonse_standard_v1",
      include_legal_basis: true,
    }),
  });
  if (!response.ok) {
    throw new Error(`analysis api ${response.status}`);
  }
  return response.json();
}

function normalizeReport(report) {
  const normalized = { ...report };
  if (!normalized.safety_checklist || normalized.safety_checklist.length === 0) {
    normalized.safety_checklist = fallbackChecklist;
  }
  normalized.safety_checklist = normalized.safety_checklist.map((group) => ({
    ...group,
    items: group.items.map((item) => ({
      ...item,
      status: state.completedChecks.has(item.id) ? "completed" : item.status || "unchecked",
    })),
  }));
  return normalized;
}

function applyFallbackScore() {
  const checklistReduction = fallbackChecklist
    .flatMap((group) => group.items)
    .filter((item) => state.completedChecks.has(item.id))
    .reduce((sum, item) => sum + item.risk_reduction_points, 0);
  const finalScore = Math.max(0, fallbackReport.risk_score.base_score + fallbackReport.risk_score.special_terms_delta - checklistReduction);
  return {
    ...fallbackReport,
    risk_overview: `계약서 내 위험 문구와 확인 필요 항목을 기준으로 참고 지표를 산출했습니다.`,
    risk_score: {
      ...fallbackReport.risk_score,
      checklist_reduction: checklistReduction,
      final_score: finalScore,
      risk_level: scoreLevel(finalScore),
    },
    safety_checklist: fallbackChecklist,
  };
}

function scoreLevel(score) {
  if (score >= 70) return "danger";
  if (score >= 35) return "warning";
  if (score >= 20) return "caution";
  return "normal";
}

function render() {
  if (!state.report) return;
  renderRisk();
  renderExtractedSummary();
  renderChecklist();
  renderActions();
  renderSpecialTerms();
  renderDocumentContent();
  renderDocumentOverlays();
}

function renderExtractedSummary() {
  const structuredItems = buildStructuredSummaryItems(state.uploadResult?.contract_fields);
  if (structuredItems.length && elements.fieldSummaryList) {
    elements.fieldSummaryList.innerHTML = "";
    structuredItems.forEach((item) => {
      const row = document.createElement("div");
      row.className = item.needsReview ? "needs-review" : "";
      const label = document.createElement("dt");
      label.textContent = item.label;
      const value = document.createElement("dd");
      value.textContent = item.value;
      row.append(label, value);
      elements.fieldSummaryList.append(row);
    });
    return;
  }

  const extraction = extractKeyInfo(state.uploadResult?.full_text || "");
  elements.contractType.textContent = extraction.contractType;
  elements.deposit.textContent = extraction.deposit;
  elements.leasePeriod.textContent = extraction.leasePeriod;
  elements.fixedDate.textContent = extraction.fixedDate;
  elements.moveIn.textContent = extraction.moveIn;
  elements.seniorRights.textContent = extraction.seniorRights;
}

function buildStructuredSummaryItems(contractFields) {
  const fields = contractFields?.fields;
  if (!fields) return [];
  const documentType = contractFields?.profile?.document_type || elements.documentType?.value || "unknown";
  const fieldOrder = SUMMARY_FIELDS_BY_TYPE[documentType] || SUMMARY_FIELDS_BY_TYPE.unknown;

  return fieldOrder
    .map((fieldId) => {
      const value = fieldId === "lease_period"
        ? buildLeasePeriod(fields.lease_start_date, fields.lease_end_date)
        : fieldDisplay(fields[fieldId]);
      return {
        fieldId,
        label: SUMMARY_FIELD_LABELS[fieldId] || fieldId,
        value,
        needsReview: fieldId === "lease_period"
          ? Boolean(fields.lease_start_date?.needs_review || fields.lease_end_date?.needs_review)
          : Boolean(fields[fieldId]?.needs_review),
      };
    })
    .filter((item) => item.value)
    .slice(0, 12);
}

function fieldDisplay(field) {
  if (!field) return "확인 필요";
  return field.display_value || field.value || "확인 필요";
}

function buildLeasePeriod(startField, endField) {
  const start = fieldDisplay(startField);
  const end = fieldDisplay(endField);
  if (start === "확인 필요" && end === "확인 필요") return "확인 필요";
  return `${start} ~ ${end}`;
}

function extractKeyInfo(text) {
  const normalized = normalizeText(text);
  if (!normalized) {
    return {
      contractType: "전세",
      deposit: "₩350,000,000",
      leasePeriod: "2026.08.01 ~ 2028.07.31",
      fixedDate: "예정",
      moveIn: "예정",
      seniorRights: "근저당 없음",
    };
  }

  return {
    contractType: detectContractType(normalized),
    deposit: extractDeposit(normalized),
    leasePeriod: extractLeasePeriod(normalized),
    fixedDate: detectFixedDate(normalized),
    moveIn: detectMoveIn(normalized),
    seniorRights: detectSeniorRights(normalized),
  };
}

function normalizeText(text) {
  return String(text || "")
    .replace(/\[REDACTED\]/g, " ")
    .replace(/[□☑✓✔]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function detectContractType(text) {
  const head = text.slice(0, 900);
  const hasJeonse = /전세|보증금\s*있는\s*월세/.test(head);
  const hasMonthly = /월세|차임/.test(head);
  if (hasJeonse && hasMonthly) return "전세/월세 후보";
  if (hasJeonse) return "전세";
  if (hasMonthly) return "월세";
  return "확인 필요";
}

function extractDeposit(text) {
  const amountPatterns = [
    /보증금\s*(?:금)?\s*([0-9,]{4,})\s*원/,
    /보증금[^0-9가-힣]{0,20}([0-9,]{4,})/,
    /금\s*([0-9,]{4,})\s*원정/,
  ];
  for (const pattern of amountPatterns) {
    const match = text.match(pattern);
    if (match?.[1]) return formatWon(match[1]);
  }

  const koreanAmount = text.match(/보증금[^가-힣]{0,20}([일이삼사오육칠팔구십백천만억\s]+)원/);
  if (koreanAmount?.[1]) {
    return `${koreanAmount[1].replace(/\s+/g, "")}원`;
  }

  return "확인 필요";
}

function formatWon(value) {
  const number = Number(String(value).replace(/[^\d]/g, ""));
  if (!Number.isFinite(number) || number <= 0) return "확인 필요";
  return `₩${number.toLocaleString("ko-KR")}`;
}

function extractLeasePeriod(text) {
  const date = "(\\d{4})[.\\-/년\\s]+(\\d{1,2})[.\\-/월\\s]+(\\d{1,2})";
  const pattern = new RegExp(`${date}[^0-9]{1,20}${date}`);
  const match = text.match(pattern);
  if (match) {
    return `${formatDateParts(match[1], match[2], match[3])} ~ ${formatDateParts(match[4], match[5], match[6])}`;
  }

  const looseDates = [...text.matchAll(/\d{4}[.\-/년\s]+\d{1,2}[.\-/월\s]+\d{1,2}/g)]
    .map((item) => item[0])
    .slice(0, 2);
  if (looseDates.length >= 2) {
    return `${cleanDate(looseDates[0])} ~ ${cleanDate(looseDates[1])}`;
  }

  if (/임대차기간|계약\s*기간/.test(text)) return "날짜 확인 필요";
  return "확인 필요";
}

function formatDateParts(year, month, day) {
  return `${year}.${String(month).padStart(2, "0")}.${String(day).padStart(2, "0")}`;
}

function cleanDate(value) {
  const parts = value.match(/(\d{4}).*?(\d{1,2}).*?(\d{1,2})/);
  return parts ? formatDateParts(parts[1], parts[2], parts[3]) : value;
}

function detectFixedDate(text) {
  if (/확정일자[^。.\n]{0,40}(완료|부여|신고필증|접수완료)/.test(text)) return "완료";
  if (/확정일자/.test(text)) return "확인 필요";
  return "예정";
}

function detectMoveIn(text) {
  if (/전입신고[^。.\n]{0,40}(완료|신청|예정일|까지)/.test(text)) return "확인 필요";
  if (/전입신고|주민등록/.test(text)) return "예정";
  return "확인 필요";
}

function detectSeniorRights(text) {
  if (/선순위[^。.\n]{0,20}없음|근저당[^。.\n]{0,20}없음/.test(text)) return "근저당 없음";
  if (/근저당|저당권|담보권|압류|가압류|선순위/.test(text)) return "확인 필요";
  return "확인 필요";
}

function renderRisk() {
  const score = state.report.risk_score;
  const label = riskLabel(score.risk_level);
  elements.headerScore.textContent = `${score.final_score}점`;
  elements.headerScoreLabel.textContent = label;
  elements.riskScore.textContent = `${score.final_score}점`;
  elements.riskFormula.textContent = `위험 문구 + 확인 필요 항목 반영`;
  elements.riskLevelPill.textContent = label;
  elements.riskLevelPill.className = `pill ${score.risk_level === "danger" ? "danger" : score.risk_level === "normal" ? "success" : "warning"}`;
}

function riskLabel(level) {
  return {
    danger: "위험",
    warning: "주의",
    caution: "주의 필요",
    normal: "정상",
  }[level] || "주의 필요";
}

function renderChecklist() {
  const completed = state.completedChecks.size;
  elements.completedCount.textContent = `${completed}개 완료`;
  elements.checklistGroups.innerHTML = "";

  state.report.safety_checklist.forEach((group) => {
    const groupEl = document.createElement("section");
    groupEl.className = "checklist-group";
    groupEl.innerHTML = `<h3>${escapeHtml(group.title)}</h3>`;

    group.items.forEach((item) => {
      const isCompleted = state.completedChecks.has(item.id) || item.status === "completed";
      const isOpened = state.openedChecks.has(item.id);
      const row = document.createElement("article");
      row.className = `check-item ${isCompleted ? "completed" : ""}`;
      row.innerHTML = `
        <div class="check-top">
          <span class="check-toggle" aria-hidden="true"></span>
          <span class="check-title">
            <strong>${escapeHtml(item.label)}</strong>
            <span>${escapeHtml(item.description || item.why_it_matters || "")}</span>
          </span>
          <span class="check-points">-${item.risk_reduction_points || 0}점</span>
        </div>
        <div class="check-actions"></div>
        ${item.external_action?.completion_hint ? `<p class="special-note">${escapeHtml(item.external_action.completion_hint)}</p>` : ""}
      `;
      const actions = row.querySelector(".check-actions");
      if (item.external_action?.url) {
        const openButton = document.createElement("button");
        openButton.className = "mini-button ghost";
        openButton.type = "button";
        openButton.textContent = isOpened ? "페이지 열림" : item.external_action.label || "확인 페이지 열기";
        openButton.addEventListener("click", () => {
          state.openedChecks.add(item.id);
          window.open(item.external_action.url, "_blank", "noopener,noreferrer");
          renderChecklist();
        });
        actions.append(openButton);
      }
      const completeButton = document.createElement("button");
      completeButton.className = "mini-button";
      completeButton.type = "button";
      completeButton.textContent = isCompleted ? "완료됨" : "확인 완료";
      completeButton.disabled = isCompleted;
      completeButton.addEventListener("click", async () => {
        state.completedChecks.add(item.id);
        await fetchReport(state.documentId);
      });
      actions.append(completeButton);
      groupEl.append(row);
    });

    elements.checklistGroups.append(groupEl);
  });
}

function renderActions() {
  elements.recommendedActions.innerHTML = "";
  (state.report.recommended_actions || []).forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    elements.recommendedActions.append(li);
  });
}

function renderSpecialTerms() {
  elements.specialTerms.innerHTML = "";
  (state.report.differences || []).forEach((difference) => {
    const card = document.createElement("article");
    card.className = "special-card";
    card.innerHTML = `
      <strong>${escapeHtml(difference.category)} · +${difference.risk_score_delta || 0}점</strong>
      <p class="special-note">${escapeHtml(difference.special_term_explanation || difference.original_text || "")}</p>
    `;
    elements.specialTerms.append(card);
  });
}

function renderDocumentContent() {
  if (state.uploadResult?.preview_pages?.length) {
    renderPreviewPages();
    return;
  }

  const blocks = Array.from(elements.documentViewer.querySelectorAll(".doc-cell, .doc-wide"));
  const { snippets, qualityLabel } = buildDocumentSnippets();
  blocks.forEach((block, index) => {
    const snippet = snippets[index];
    block.classList.toggle("has-ocr-text", Boolean(snippet));
    block.textContent = snippet || "";
  });

  const toolbar = elements.documentViewer.querySelector(".doc-toolbar");
  if (!toolbar) return;
  const locationCount = state.uploadResult?.text_locations?.length || 0;
  const redactionCount =
    state.uploadResult?.redaction_metrics?.total_redaction_count ||
    state.uploadResult?.redactions?.length ||
    0;
  toolbar.textContent = state.uploadResult
    ? `OCR ${locationCount}개 · 마스킹 ${redactionCount}개 · ${qualityLabel}`
    : "업로드 후 OCR 결과 표시";
}

function renderPreviewPages() {
  const pages = state.uploadResult?.preview_pages || [];
  const locationCount = state.uploadResult?.text_locations?.length || 0;
  const redactionCount =
    state.uploadResult?.redaction_metrics?.total_redaction_count ||
    state.uploadResult?.redactions?.length ||
    0;

  elements.documentViewer.innerHTML = "";
  const toolbar = document.createElement("div");
  toolbar.className = "doc-toolbar";
  toolbar.textContent = `OCR ${locationCount}개 · 마스킹 ${redactionCount}개 · 원본 보기`;
  elements.documentViewer.append(toolbar);

  const stack = document.createElement("div");
  stack.className = "preview-stack";
  pages.forEach((page) => {
    const pageEl = document.createElement("section");
    pageEl.className = "preview-page";
    pageEl.dataset.pageNumber = String(page.page_number);
    pageEl.dataset.width = String(page.width);
    pageEl.dataset.height = String(page.height);
    pageEl.dataset.coordinateSystem = page.coordinate_system || "";
    pageEl.tabIndex = 0;
    pageEl.title = "클릭해서 크게 보기";
    pageEl.innerHTML = `
      <img src="${page.image_data_url}" alt="계약서 ${page.page_number}페이지" />
      <div class="preview-overlay"></div>
      <span class="page-badge">${page.page_number}</span>
    `;
    pageEl.addEventListener("click", () => openPreviewZoom(pageEl));
    pageEl.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openPreviewZoom(pageEl);
      }
    });
    stack.append(pageEl);
  });
  elements.documentViewer.append(stack);
}

function buildDocumentSnippets() {
  const locations = state.uploadResult?.text_locations || [];
  const locationSnippets = locations
    .filter((item) => item.confidence == null || item.confidence >= 0.35)
    .map((item) => normalizeSnippet(item.text))
    .filter(isReadableContractSnippet);

  if (locationSnippets.length > 0) {
    return {
      snippets: uniqueSnippets(locationSnippets).slice(0, 7),
      qualityLabel: "문장 인식",
    };
  }

  const fullText = state.uploadResult?.full_text || "";
  if (fullText) {
    const textSnippets = uniqueSnippets(
      fullText
        .split(/\n|(?<=다\.)|(?<=요\.)/)
        .map(normalizeSnippet)
        .filter(isReadableContractSnippet),
    ).slice(0, 7);
    if (textSnippets.length > 0) {
      return {
        snippets: textSnippets,
        qualityLabel: "문장 인식",
      };
    }
    return {
      snippets: [
        "한글 문장 인식률이 낮아 원문 미리보기를 숨겼습니다.",
        "촬영 각도, 그림자, 손글씨 품질에 따라 OCR 결과가 흔들릴 수 있습니다.",
        "핵심 정보는 확인 필요로 표시하고 체크리스트를 통해 보완 확인을 진행하세요.",
      ],
      qualityLabel: "품질 낮음",
    };
  }

  return {
    snippets: [
      "계약서 업로드 후 OCR로 추출된 문장이 여기에 표시됩니다.",
      "핵심 정보와 개인정보 마스킹 박스가 계약서 보기 영역에 연결됩니다.",
      "위험 특약은 노란색 또는 빨간색 박스로 표시됩니다.",
    ],
    qualityLabel: "대기",
  };
}

function normalizeSnippet(value) {
  return String(value || "")
    .replace(/\[REDACTED\]/g, "마스킹")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 90);
}

function uniqueSnippets(values) {
  const seen = new Set();
  return values.filter((value) => {
    const key = value.replace(/\s+/g, "");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function isReadableContractSnippet(value) {
  const text = normalizeSnippet(value);
  if (text.length < 8) return false;
  if (/^[A-Za-z0-9.,:;'"()[\]\s-]+$/.test(text)) return false;

  const hangulCount = (text.match(/[가-힣]/g) || []).length;
  const digitCount = (text.match(/\d/g) || []).length;
  const usefulCount = hangulCount + digitCount;
  const compactLength = text.replace(/\s/g, "").length || 1;
  const usefulRatio = usefulCount / compactLength;

  if (hangulCount >= 4 && usefulRatio >= 0.25) return true;
  if (digitCount >= 6 && /원|보증금|계약|기간|주소|월|일/.test(text)) return true;
  return false;
}

function renderDocumentOverlays() {
  if (state.uploadResult?.preview_pages?.length) {
    renderPreviewOverlays();
    return;
  }

  elements.documentViewer.querySelectorAll(".redaction-box, .highlight-box").forEach((node) => node.remove());
  const redactions = state.uploadResult?.redactions || [];
  redactions.slice(0, 10).forEach((redaction, index) => {
    const box = document.createElement("span");
    box.className = "redaction-box";
    const placement = mockPlacement(index, redactions.length);
    Object.assign(box.style, placement);
    elements.documentViewer.append(box);
  });

  const differences = state.report?.differences || [];
  differences.forEach((difference, index) => {
    const box = document.createElement("span");
    box.className = `highlight-box ${difference.risk_level === "high" ? "high" : "medium"}`;
    Object.assign(box.style, mockHighlightPlacement(index));
    elements.documentViewer.append(box);
  });
}

function renderPreviewOverlays() {
  elements.documentViewer.querySelectorAll(".preview-overlay").forEach((overlay) => {
    overlay.innerHTML = "";
  });

  const redactions = state.uploadResult?.redactions || [];
  redactions.forEach((redaction) => {
    const pageEl = elements.documentViewer.querySelector(
      `.preview-page[data-page-number="${redaction.page_number}"]`,
    );
    if (!pageEl) return;
    if (!isCompatibleCoordinateSystem(redaction.coordinate_system, pageEl.dataset.coordinateSystem)) return;

    const box = bboxToPercentBox(redaction.value_bbox, pageEl);
    if (!box) return;
    const overlay = pageEl.querySelector(".preview-overlay");
    const mask = document.createElement("span");
    mask.className = `redaction-box ${redaction.mask_style || "opaque"} ${redaction.sensitivity || "high"}`;
    mask.title = redaction.label_text || redaction.label_type || "masked";
    Object.assign(mask.style, box);
    overlay.append(mask);
  });

  collectFieldEvidenceBoxes().forEach((evidence) => {
    const pageEl = elements.documentViewer.querySelector(
      `.preview-page[data-page-number="${evidence.page_number}"]`,
    );
    if (!pageEl) return;
    if (!isCompatibleCoordinateSystem(evidence.coordinate_system, pageEl.dataset.coordinateSystem)) return;
    const bbox = evidence.value_bbox?.length === 4 ? evidence.value_bbox : evidence.bbox;
    const box = normalizeEvidenceBox(bboxToPercentBox(bbox, pageEl), evidence.field_id);
    if (!box) return;
    const overlay = pageEl.querySelector(".preview-overlay");
    const marker = document.createElement("span");
    marker.className = `field-evidence-box ${fieldEvidenceClass(evidence.field_id)}`;
    marker.title = SUMMARY_FIELD_LABELS[evidence.field_id] || evidence.label_text || "추출 필드";
    Object.assign(marker.style, box);
    overlay.append(marker);
  });
}

function collectFieldEvidenceBoxes() {
  const visibleFieldIds = new Set([
    "land_area",
    "building_info",
    "lease_area",
    "deposit_amount",
    "monthly_rent",
    "sale_price",
    "contract_payment",
    "intermediate_payment",
    "balance_payment",
    "lease_start_date",
    "lease_end_date",
    "special_terms",
    "risk_flags",
  ]);
  const fields = state.uploadResult?.contract_fields?.fields || {};
  return Object.entries(fields)
    .filter(([fieldId]) => visibleFieldIds.has(fieldId))
    .flatMap(([fieldId, field]) => (field?.evidence || []).map((evidence) => ({ ...evidence, field_id: fieldId })))
    .filter((evidence) => !isBrokerageOnlyEvidence(evidence))
    .filter((evidence) => evidence?.page_number && (evidence.value_bbox?.length === 4 || evidence.bbox?.length === 4));
}

function isBrokerageOnlyEvidence(evidence) {
  if (!["special_terms", "risk_flags"].includes(evidence.field_id)) return false;
  const text = String(evidence.text || evidence.value_text || "");
  return /중개보수|중개수수료|거래가액/.test(text);
}

function fieldEvidenceClass(fieldId) {
  if (["land_area", "building_info", "lease_area", "address"].includes(fieldId)) return "property";
  if (["special_terms", "risk_flags"].includes(fieldId)) return "special";
  if (
    [
      "deposit_amount",
      "monthly_rent",
      "sale_price",
      "contract_payment",
      "intermediate_payment",
      "balance_payment",
    ].includes(fieldId)
  ) {
    return "payment";
  }
  return "general";
}

function isCompatibleCoordinateSystem(source, target) {
  if (!source || !target) return false;
  if (source === target) return true;
  return source.includes(target) || target.includes(source);
}

function bboxToPercentBox(bbox, pageEl) {
  if (!Array.isArray(bbox) || bbox.length !== 4) return null;
  const width = Number(pageEl.dataset.width);
  const height = Number(pageEl.dataset.height);
  if (!width || !height) return null;
  const [x0, y0, x1, y1] = bbox.map(Number);
  if (![x0, y0, x1, y1].every(Number.isFinite) || x1 <= x0 || y1 <= y0) return null;
  return {
    left: `${clamp((x0 / width) * 100, 0, 100)}%`,
    top: `${clamp((y0 / height) * 100, 0, 100)}%`,
    width: `${clamp(((x1 - x0) / width) * 100, 0, 100)}%`,
    height: `${clamp(((y1 - y0) / height) * 100, 0, 100)}%`,
  };
}

function normalizeEvidenceBox(box, fieldId) {
  if (!box) return null;
  const left = parseFloat(box.left);
  const top = parseFloat(box.top);
  const width = parseFloat(box.width);
  const height = parseFloat(box.height);
  if (![left, top, width, height].every(Number.isFinite)) return box;

  const presets = {
    land_area: { padX: 5, minWidth: 38, minHeight: 1.9 },
    building_info: { padX: 5, minWidth: 42, minHeight: 1.9 },
    lease_area: { padX: 5, minWidth: 38, minHeight: 1.9 },
    deposit_amount: { padX: 3, minWidth: 34, minHeight: 1.9 },
    contract_payment: { padX: 3, minWidth: 34, minHeight: 1.9 },
    intermediate_payment: { padX: 3, minWidth: 34, minHeight: 1.9 },
    balance_payment: { padX: 3, minWidth: 34, minHeight: 1.9 },
    monthly_rent: { padX: 3, minWidth: 34, minHeight: 1.9 },
    lease_start_date: { padX: 4, minWidth: 54, minHeight: 2.1 },
    lease_end_date: { padX: 4, minWidth: 54, minHeight: 2.1 },
    special_terms: { padX: 2, minWidth: 62, minHeight: 5 },
    risk_flags: { padX: 2, minWidth: 62, minHeight: 5 },
  };
  const preset = presets[fieldId];
  if (!preset) return box;

  const nextLeft = clamp(left - preset.padX, 0, 100);
  const targetWidth = Math.max(width + preset.padX * 2, preset.minWidth);
  const nextWidth = clamp(Math.min(targetWidth, 100 - nextLeft), 0, 100);
  const nextHeight = Math.max(height, preset.minHeight);
  const nextTop = clamp(top - Math.max(0, nextHeight - height) / 2, 0, 100);
  return {
    left: `${nextLeft}%`,
    top: `${nextTop}%`,
    width: `${nextWidth}%`,
    height: `${clamp(nextHeight, 0, 100 - nextTop)}%`,
  };
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function mockPlacement(index) {
  const top = 86 + index * 38;
  const left = index % 2 === 0 ? 8 : 52;
  return {
    top: `${Math.min(top, 510)}px`,
    left: `${left}%`,
    width: "32%",
    height: "22px",
  };
}

function mockHighlightPlacement(index) {
  return {
    top: `${index === 0 ? 500 : 210}px`,
    left: "4%",
    width: index === 0 ? "92%" : "44%",
    height: index === 0 ? "70px" : "58px",
  };
}

function setStatus(text) {
  elements.status.textContent = text;
}

function openPreviewZoom(pageEl) {
  const modal = getPreviewZoomModal();
  const body = modal.querySelector(".preview-zoom-body");
  const title = modal.querySelector(".preview-zoom-title");
  body.innerHTML = "";
  const clone = pageEl.cloneNode(true);
  clone.removeAttribute("tabindex");
  clone.removeAttribute("title");
  title.textContent = `${pageEl.dataset.pageNumber || ""}페이지 확대 보기`;
  body.append(clone);
  modal.classList.remove("hidden");
  document.body.classList.add("modal-open");
}

function closePreviewZoom() {
  const modal = document.querySelector(".preview-zoom-modal");
  if (!modal) return;
  modal.classList.add("hidden");
  modal.querySelector(".preview-zoom-body").innerHTML = "";
  document.body.classList.remove("modal-open");
}

function getPreviewZoomModal() {
  let modal = document.querySelector(".preview-zoom-modal");
  if (modal) return modal;
  modal = document.createElement("div");
  modal.className = "preview-zoom-modal hidden";
  modal.innerHTML = `
    <div class="preview-zoom-backdrop" data-close-preview-zoom="true"></div>
    <section class="preview-zoom-panel" aria-modal="true" role="dialog">
      <header class="preview-zoom-header">
        <strong class="preview-zoom-title">계약서 확대 보기</strong>
        <button class="preview-zoom-close" type="button" aria-label="닫기">×</button>
      </header>
      <div class="preview-zoom-body"></div>
    </section>
  `;
  modal.addEventListener("click", (event) => {
    if (event.target.closest(".preview-zoom-close") || event.target.dataset.closePreviewZoom) {
      closePreviewZoom();
    }
  });
  document.body.append(modal);
  return modal;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function downloadReport() {
  if (!state.report) return;
  const payload = JSON.stringify(state.report, null, 2);
  const blob = new Blob([payload], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${state.documentId}-risk-report.json`;
  link.click();
  URL.revokeObjectURL(url);
}

elements.fileInput.addEventListener("change", (event) => {
  const [file] = event.target.files;
  state.selectedFile = file || null;
  if (!file) {
    elements.fileName.textContent = "계약서를 선택하세요";
    elements.fileMeta.textContent = "선택 후 분석 실행";
    return;
  }
  elements.fileName.textContent = file.name;
  elements.fileMeta.textContent = `${(file.size / 1024 / 1024).toFixed(1)}MB · 분석 대기`;
});

elements.analyzeButton.addEventListener("click", uploadSelectedFile);
elements.downloadReport.addEventListener("click", downloadReport);

elements.loginButton?.addEventListener("click", handleLogin);
elements.signupButton?.addEventListener("click", handleSignup);
elements.logoutButton?.addEventListener("click", () => {
  clearAuthSession();
  setStatus("로그아웃되었습니다.");
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closePreviewZoom();
});

renderAuth();
fetchReport(DEMO_DOCUMENT_ID);
