# EpiScope AI Prompt Documentation



## 1. End-to-End Project Development

**Prompt**

> Review the attached CSE 4345 Complex Engineering Problem assignment, “EpiScope,” and use it as the authoritative source for project requirements. Develop a student-scale, explainable prototype that demonstrates an end-to-end disease-surveillance workflow using a reproducible synthetic data generator, a PySpark bronze/silver/gold pipeline, baseline analytics, aggregated serving data, and a D3.js dashboard.
>
> Prepare supporting technical documentation, including a project proposal, report draft, policy brief, AI-use disclosure, and presentation run sheet. Clearly distinguish implemented features from incomplete requirements. Do not fabricate performance measurements, public-data provenance, user-study findings, student contributions, signatures, repository history, or a presentation recording.
>

**Applied to:** Initial repository scaffold, generator, pipeline, analytics, dashboard, and supporting documentation.

## 2. Professional README

**Prompt**

> Rewrite the project README as a professional and informative landing page for EpiScope. Include a concise project overview, features, architecture, prerequisites, Windows setup and run instructions, dashboard access, data and privacy notes, current implementation status, limitations, requirement traceability, team and presentation information, and links to project documentation.
>
> Ensure every instruction matches the files and behavior in the repository. Clearly label synthetic results and incomplete evaluation. Do not imply the prototype is production-ready or that pending deliverables are complete.

**Applied to:** README.md.

## 3. Dashboard Design Improvement

**Prompt**

> Improve the EpiScope dashboard’s visual design to make it polished, accessible, and suitable for a public-health decision-support prototype. Establish a clear information hierarchy, consistent typography and spacing, refined colors, responsive layouts, readable charts and tables, and clear status and privacy notices.
>
> Preserve the existing D3.js v7 visualizations, data schema, and district/disease/horizon interactions. Make any changes to controls work with the existing dashboard code. Clearly identify synthetic data, schematic geography, uncertain estimates, and unvalidated warning signals. Do not present prototype outputs as official health information.

**Applied to:** dashboard/index.html, dashboard/style.css, and dashboard/app.js.

## 4. Run and Error Support

**Prompt**

> Review the provided terminal output from running EpiScope. Identify the first actionable error, distinguish it from non-blocking warnings and cleanup messages, and provide the smallest safe correction. Keep recommendations consistent with the pinned Python and Spark versions and the supported Java runtime. After correcting a project-code defect, explain how to resume from the completed pipeline stage without unnecessarily duplicating data.

**Applied to:** Java/Spark compatibility guidance and correction of the analytics script syntax error.

## Responsible-use note

These prompts document AI-assisted contributions; they do not establish student authorship or independently validated results. Each team member should review the project, understand and adapt the code, make genuine contributions, and add any other AI tools or prompts used by the group.
