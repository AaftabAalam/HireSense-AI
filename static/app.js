const resumeForm = document.getElementById("resume-form");
const resumeFileInput = document.getElementById("resume-file");
const uploadStatus = document.getElementById("upload-status");
const answerStatus = document.getElementById("answer-status");
const chatLog = document.getElementById("chat-log");
const interviewShell = document.getElementById("interview-shell");
const questionBadge = document.getElementById("question-badge");
const candidateMeta = document.getElementById("candidate-meta");
const resumeSkills = document.getElementById("resume-skills");
const liveScores = document.getElementById("live-scores");
const liveSummary = document.getElementById("live-summary");
const reportLinks = document.getElementById("report-links");
const recordBtn = document.getElementById("record-btn");
const launchBtn = document.getElementById("launch-btn");
const resumeFeedback = document.getElementById("resume-feedback");
const voiceOrb = document.getElementById("voice-orb");

let uploadId = null;
let sessionId = null;
let recorder = null;
let recordedChunks = [];
let isRecording = false;

function appendMessage(role, content) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;
  bubble.textContent = content;
  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function setOrbState(state) {
  voiceOrb.classList.remove("speaking", "recording");
  if (state) voiceOrb.classList.add(state);
}

function speakMessage(content) {
  if (!("speechSynthesis" in window) || !content) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(content);
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.onstart = () => setOrbState("speaking");
  utterance.onend = () => setOrbState("");
  window.speechSynthesis.speak(utterance);
}

function renderProfile(profile) {
  candidateMeta.innerHTML = `
    <p><strong>${profile.candidate_name || "Candidate"}</strong></p>
    <p>${profile.title || "Technical interview candidate"}</p>
    <p>${profile.summary || "Resume parsed successfully."}</p>
  `;
  resumeSkills.innerHTML = "";
  (profile.skills || []).forEach((skill) => {
    const pill = document.createElement("span");
    pill.className = "skill-pill";
    pill.textContent = skill;
    resumeSkills.appendChild(pill);
  });
}

function renderResumeFeedback(profile) {
  resumeFeedback.classList.remove("hidden");
  const skills = (profile.skills || []).slice(0, 8).join(", ") || "No strong technical skills were extracted.";
  resumeFeedback.innerHTML = `
    <p><strong>Resume feedback</strong></p>
    <p>The AI extracted the candidate profile and is ready to build a targeted 3-question interview.</p>
    <p><strong>Role focus:</strong> ${profile.title || "General technical profile"}</p>
    <p><strong>Detected skills:</strong> ${skills}</p>
  `;
}

function renderEvaluation(evaluation) {
  if (!evaluation) return;
  const scorecard = evaluation.scorecard || {};
  liveScores.innerHTML = "";
  [
    ["Communication", scorecard.communication],
    ["Technical relevance", scorecard.technical_relevance],
    ["Confidence", scorecard.confidence],
    ["Clarity", scorecard.clarity],
    ["Overall quality", scorecard.overall_quality],
    ["Resume match", evaluation.relevance_score],
  ].forEach(([label, value]) => {
    const card = document.createElement("div");
    card.className = "score-card";
    card.innerHTML = `<strong>${label}</strong><div>${value ?? "-"}</div>`;
    liveScores.appendChild(card);
  });

  liveSummary.innerHTML = "";
  (evaluation.feedback_summary || []).forEach((item) => {
    const bullet = document.createElement("span");
    bullet.textContent = item;
    liveSummary.appendChild(bullet);
  });
}

function renderReportLinks(reply) {
  reportLinks.innerHTML = "";
  if (reply.report_path) {
    const htmlLink = document.createElement("a");
    htmlLink.href = `/${reply.report_path}`;
    htmlLink.target = "_blank";
    htmlLink.rel = "noreferrer";
    htmlLink.textContent = "Open HTML report";
    reportLinks.appendChild(htmlLink);
  }
  if (reply.report_json_path) {
    const jsonLink = document.createElement("a");
    jsonLink.href = `/${reply.report_json_path}`;
    jsonLink.target = "_blank";
    jsonLink.rel = "noreferrer";
    jsonLink.textContent = "Open JSON report";
    reportLinks.appendChild(jsonLink);
  }
}

resumeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!resumeFileInput.files.length) {
    uploadStatus.textContent = "Please choose a resume file first.";
    return;
  }

  uploadStatus.textContent = "Uploading and analyzing the resume...";
  const formData = new FormData();
  formData.append("resume", resumeFileInput.files[0]);

  const response = await fetch("/api/resume/analyze", { method: "POST", body: formData });
  if (!response.ok) {
    uploadStatus.textContent = "Resume analysis failed. Check the backend logs.";
    return;
  }

  const payload = await response.json();
  uploadId = payload.upload_id;
  renderResumeFeedback(payload.resume_profile);
  renderProfile(payload.resume_profile);
  launchBtn.classList.remove("hidden");
  uploadStatus.textContent = "Resume analyzed. Review the feedback, then launch the AI voice interview.";
});

launchBtn.addEventListener("click", async () => {
  if (!uploadId) {
    uploadStatus.textContent = "Analyze a resume before launching the interview.";
    return;
  }

  const formData = new FormData();
  formData.append("upload_id", uploadId);
  const response = await fetch("/api/interview/start", { method: "POST", body: formData });
  if (!response.ok) {
    uploadStatus.textContent = "Interview launch failed. Check backend logs.";
    return;
  }

  const payload = await response.json();
  sessionId = payload.session_id;
  interviewShell.classList.remove("hidden");
  chatLog.innerHTML = "";
  liveScores.innerHTML = "";
  liveSummary.innerHTML = "";
  reportLinks.innerHTML = "";
  questionBadge.textContent = "Question 1 / 3";
  appendMessage("assistant", payload.message);
  speakMessage(payload.message);
  answerStatus.textContent = "The AI interviewer is speaking. When ready, record the candidate's spoken answer.";
  uploadStatus.textContent = "AI voice interview launched successfully.";
});

recordBtn.addEventListener("click", async () => {
  if (!sessionId) {
    answerStatus.textContent = "Launch the interview before recording an answer.";
    return;
  }

  if (!isRecording) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);
    recordedChunks = [];
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) recordedChunks.push(event.data);
    };
    recorder.onstop = async () => {
      setOrbState("");
      const blob = new Blob(recordedChunks, { type: "audio/webm" });
      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("audio", blob, "answer.webm");
      answerStatus.textContent = "Transcribing and evaluating the spoken answer...";
      const response = await fetch("/api/interview/respond-audio", { method: "POST", body: formData });
      const reply = await response.json();
      if (reply.transcribed_answer) appendMessage("user", reply.transcribed_answer);
      appendMessage("assistant", reply.assistant_message);
      speakMessage(reply.assistant_message);
      renderEvaluation(reply.latest_evaluation);
      renderReportLinks(reply);
      const nextPosition = Math.min((reply.current_question_index || 0) + 1, 3);
      questionBadge.textContent = `Question ${nextPosition} / 3`;
      answerStatus.textContent =
        reply.status === "completed"
          ? "Interview finished. The final report is ready."
          : reply.latest_evaluation?.answer_status === "clarification_needed"
            ? "Clarification provided. The same question is still active."
            : "Spoken answer processed. The interviewer is asking the next question.";
      stream.getTracks().forEach((track) => track.stop());
    };
    recorder.start();
    isRecording = true;
    recordBtn.textContent = "Stop Recording";
    setOrbState("recording");
    answerStatus.textContent = "Recording candidate answer...";
  } else {
    recorder.stop();
    isRecording = false;
    recordBtn.textContent = "Record Answer";
  }
});
