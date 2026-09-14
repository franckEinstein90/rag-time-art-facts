# CareerAgent POC Requirements

Status: draft baseline  
Product area: CareerAgent job description analyzer POC  
Scope: Streamlit-based proof of concept for analyzing job descriptions, tailoring application materials, and organizing generated artifacts into application folders.

## 1. Product Objective

### 1.1 Purpose

1.1.1. The system shall help a job seeker analyze copied job descriptions and generate practical application artifacts.

1.1.2. The system shall reduce repeated manual work when evaluating roles, preparing cover letters, creating requirement ledgers, and starting application folders.

1.1.3. The system shall support a proof-of-concept workflow running locally, with files saved to user-selected local or OneDrive-backed folders.

### 1.2 Target User

1.2.1. The primary user shall be an individual job seeker managing multiple active job applications.

1.2.2. The system shall assume the user has a long-form resume source document and wants tailored outputs for each job opportunity.

1.2.3. The system shall support technical and AI/software roles where job descriptions may include large skill, tool, domain, and experience requirements.

## 2. Job Description Input

### 2.1 Job Description Capture

2.1.1. The system shall provide a text input area for pasting a full job description.

2.1.2. The system shall preserve the pasted job description while navigating between app pages during the current session.

2.1.3. The system shall display a word count for the pasted job description.

2.1.4. The system shall provide an action to clear both the pasted job description and generated analysis outputs.

### 2.2 Input Validation

2.2.1. The system shall disable analysis and application-start actions when no job description has been provided.

2.2.2. The system shall warn the user when an action requires job description text and none is available.

## 3. Model Configuration

### 3.1 Model Discovery

3.1.1. The system shall detect available LLM providers based on configured API keys.

3.1.2. The system shall support OpenAI models when `OPENAI_API_KEY` is configured.

3.1.3. The system shall support Cohere models when `COHERE_API_KEY` is configured.

3.1.4. The system shall show an unavailable-state message when no supported API key is configured.

### 3.2 Model Selection

3.2.1. The system shall let the user select an active model from available registered models.

3.2.2. The system shall display the selected model provider.

3.2.3. The system shall display the selected model context window.

3.2.4. The system shall use the selected active model for metadata extraction, analysis generation, cover letter generation, and custom resume generation.

## 4. Resume Upload And Resume Context

### 4.1 Resume Upload

4.1.1. The system shall provide a Resume Viewer page.

4.1.2. The system shall accept uploaded Word `.docx` resumes.

4.1.3. The system shall reject unsupported resume file types.

4.1.4. The system shall extract readable text from the uploaded `.docx` resume.

4.1.5. The system shall display the extracted resume text.

4.1.6. The system shall provide a download action for the extracted resume text.

### 4.2 Resume Vector Index

4.2.1. The system shall chunk extracted resume text into overlapping chunks.

4.2.2. The system shall embed resume chunks using an embedding model.

4.2.3. The system shall store a FAISS vector index for the uploaded resume.

4.2.4. The system shall store chunk metadata alongside the FAISS index.

4.2.5. The system shall rebuild the vector index when the uploaded resume file changes.

4.2.6. The system shall expose a resume fingerprint that changes when the on-disk resume index changes.

### 4.3 Resume-Aware Retrieval

4.3.1. The system shall retrieve relevant resume excerpts for a job description or custom question.

4.3.2. The system shall include retrieved resume excerpts in analysis prompts when available.

4.3.3. The system shall continue analysis without resume context when no resume index is available.

4.3.4. The system shall warn the user when resume vector search fails.

4.3.5. The system shall indicate when a generated response included resume context.

## 5. User Profile Settings

### 5.1 Profile Storage

5.1.1. The system shall store user profile settings in a local SQLite database.

5.1.2. The system shall support profile fields for name, email, phone, LinkedIn, and GitHub.

5.1.3. The system shall omit blank profile values when loading the profile.

5.1.4. The system shall update existing profile settings without duplicating keys.

### 5.2 Profile Usage

5.2.1. The system shall use the stored user profile when generating cover letter envelopes.

5.2.2. The system shall use the stored user name when naming application-specific documents.

5.2.3. The system shall regenerate cover letter output when relevant profile values change.

## 6. Standard Job Analysis Tools

### 6.1 Tool Set

6.1.1. The system shall provide a Role Summary tool.

6.1.2. The system shall provide a Requirements tool.

6.1.3. The system shall provide a Tech Stack tool.

6.1.4. The system shall provide a Red Flags tool.

6.1.5. The system shall provide an Interview Prep tool.

6.1.6. The system shall provide a Cover Letter Draft tool.

6.1.7. The system shall provide a Compensation & Benefits tool.

### 6.2 Analysis Generation

6.2.1. The system shall generate analysis output by combining the pasted job description, tool-specific instructions, and optional resume context.

6.2.2. The system shall stream generated output into the UI while the model response is being produced.

6.2.3. The system shall cache each tool result in session state.

6.2.4. The system shall reuse cached results when the job description, resume fingerprint, and relevant profile fingerprint have not changed.

6.2.5. The system shall rerun a tool when the user requests regeneration.

6.2.6. The system shall provide a clear-all action for generated tool results.

### 6.3 Role Summary Requirements

6.3.1. The Role Summary tool shall produce a concise summary of the company, role responsibilities, and desired candidate profile.

6.3.2. The Role Summary tool shall include a resume-alignment sentence when resume context is available.

### 6.4 Requirements Requirements

6.4.1. The Requirements tool shall produce a technical requirements accounting document.

6.4.2. The Requirements tool shall separate must-have requirements from nice-to-have requirements.

6.4.3. The Requirements tool shall include evidence markers for resume alignment when resume context is available.

6.4.4. The Requirements tool shall speak in the first person where it summarizes the user's alignment with the role.

### 6.5 Tech Stack Requirements

6.5.1. The Tech Stack tool shall extract technologies, programming languages, frameworks, platforms, and tools from the job description.

6.5.2. The Tech Stack tool shall group extracted technologies by category.

6.5.3. The Tech Stack tool shall note whether resume excerpts confirm experience with each technology when resume context is available.

### 6.6 Red Flags Requirements

6.6.1. The Red Flags tool shall identify concerns from the candidate's perspective.

6.6.2. The Red Flags tool shall consider vague responsibilities, excessive requirements, culture concerns, and unusual expectations.

6.6.3. The Red Flags tool shall relate concerns to the user's resume context when available.

### 6.7 Interview Prep Requirements

6.7.1. The Interview Prep tool shall generate likely interview questions based on the job description.

6.7.2. The Interview Prep tool shall include both technical and behavioral questions.

6.7.3. The Interview Prep tool shall explain what each question is likely assessing.

6.7.4. The Interview Prep tool shall tailor some questions and talking points to the user's resume context when available.

### 6.8 Cover Letter Requirements

6.8.1. The Cover Letter tool shall generate the body of a professional cover letter.

6.8.2. The system shall generate the cover letter header and footer deterministically from profile data.

6.8.3. The model shall not be responsible for generating sender contact details or signature text.

6.8.4. The system shall include a `Re:` line using the extracted job title and company when available.

6.8.5. The system shall strip any duplicate LLM-generated closing signature before appending the deterministic footer.

### 6.9 Compensation Requirements

6.9.1. The Compensation & Benefits tool shall extract concrete compensation and benefits details from the job description.

6.9.2. The Compensation & Benefits tool shall identify missing or unclear compensation and benefits details.

6.9.3. The Compensation & Benefits tool shall suggest focused recruiter questions about compensation and benefits.

## 7. Custom Questions

### 7.1 Custom Question Input

7.1.1. The system shall provide a custom question input for asking arbitrary questions about the pasted job description.

7.1.2. The system shall require non-blank custom question text before submitting.

### 7.2 Custom Question Generation

7.2.1. The system shall generate a model answer using the pasted job description.

7.2.2. The system shall retrieve resume context using the custom question text when resume context is available.

7.2.3. The system shall display whether resume context was included.

7.2.4. The system shall cache the latest custom question answer during the session.

## 8. Start Application Workflow

### 8.1 Metadata Extraction

8.1.1. The system shall provide a Start Application action once a job description has been pasted.

8.1.2. The system shall use the active model to extract the job title from the pasted job description.

8.1.3. The system shall use the active model to extract the company name from the pasted job description.

8.1.4. The system shall use the active model to extract the posting date from the pasted job description.

8.1.5. The system shall default the posting date to the current date when no parseable posting date is returned.

8.1.6. The system shall extract a source URL from the pasted job description when present.

### 8.2 Application Dialog

8.2.1. The system shall open a dialog after metadata extraction.

8.2.2. The dialog shall allow the user to review and edit job title, company, posting date, application status, and storage location.

8.2.3. The default application status shall be `Ongoing`.

8.2.4. The dialog shall provide status options for `Ongoing`, `Completed`, and `Close`.

8.2.5. The dialog shall show a preview of the folder name before creation.

8.2.6. The dialog shall require non-blank job title and company values before creating a folder.

8.2.7. The dialog shall provide a folder browse action where the local environment supports it.

### 8.3 Folder Creation

8.3.1. The system shall create the application folder under the selected base path.

8.3.2. The system shall sanitize folder names for Windows compatibility.

8.3.3. The system shall avoid Windows reserved device names.

8.3.4. The system shall create a unique folder name when a matching folder already exists.

8.3.5. The application folder name shall follow the pattern `Job Title - Company - Status - YYYY-MM-DD`.

8.3.6. The system shall remember the last selected base path for later use.

## 9. Application Folder Artifacts

### 9.1 Source Files

9.1.1. The system shall save the original pasted job description as `original_description.txt`.

9.1.2. The system shall save application metadata as `application_details.json`.

9.1.3. The metadata file shall include title, company, posting date, status, source URL, and description file name.

### 9.2 Analysis Document Export

9.2.1. The system shall export cached analysis outputs into `.docx` files when creating the application folder.

9.2.2. The system shall skip analysis tools with no cached content.

9.2.3. The system shall preserve paragraph breaks in exported `.docx` documents.

9.2.4. The system shall convert simple Markdown bold and italic markers into styled Word runs.

9.2.5. The system shall remove emoji from generic analysis document headings.

### 9.3 Document Naming

9.3.1. The cover letter file name shall follow the pattern `Company_Applicant_Month_Year_COVER_LETTER.docx`.

9.3.2. The technical requirements ledger file name shall follow the pattern `Company_Applicant_Technical_Requirement_Ledger_Month_Year.docx`.

9.3.3. The custom resume file name shall follow the pattern `Company_Applicant_Month_Year_RESUME`.

9.3.4. Applicant names in generated file names shall replace spaces with underscores where the existing naming convention does so.

9.3.5. Generated file names shall be sanitized for Windows compatibility.

## 10. Custom Resume Generation

### 10.1 Resume Inputs

10.1.1. The system shall use a long-form resume `.docx` as the source of detailed user career information.

10.1.2. The system shall read the long-form resume from the configured local Windows path.

10.1.3. The system shall extract paragraph and table text from the long-form resume.

10.1.4. The system shall use the pasted job description as the target role input.

10.1.5. The system shall use the configured LaTeX template as the target resume format.

10.1.6. The system shall use the configured resume-generation prompt file to instruct the model.

### 10.2 LaTeX Generation

10.2.1. The system shall ask the active model to generate a tailored resume as complete LaTeX source code.

10.2.2. The system shall instruct the model to return only LaTeX source code.

10.2.3. The system shall strip Markdown code fences if the model returns fenced LaTeX anyway.

10.2.4. The system shall validate that the generated result resembles a complete LaTeX document before saving it.

10.2.5. The system shall save the tailored LaTeX resume into the application folder.

### 10.3 PDF Compilation

10.3.1. The system shall attempt to compile the generated LaTeX resume into a PDF.

10.3.2. The system shall support common LaTeX engines available on the Streamlit process path, including `latexmk`, `tectonic`, `pdflatex`, and `xelatex`.

10.3.3. The system shall save the resulting PDF in the same application folder when compilation succeeds.

10.3.4. The system shall remove common LaTeX scratch files after successful compilation.

10.3.5. The system shall write a build log when PDF compilation fails.

10.3.6. Failure to compile the PDF shall not prevent creation of the application folder or saving of the generated `.tex` file.

## 11. Application Viewer

### 11.1 Folder Selection

11.1.1. The system shall provide an Application Viewer page.

11.1.2. The Application Viewer shall allow the user to enter or browse for an application folder.

11.1.3. The Application Viewer shall validate that the selected path exists and is a folder.

### 11.2 File Inspection

11.2.1. The Application Viewer shall list files and subfolders in the selected application folder.

11.2.2. The file list shall include item name, type, size, and modified time.

11.2.3. The Application Viewer shall highlight likely application documents such as resumes, cover letters, application details, and descriptions.

### 11.3 Status Management

11.3.1. The Application Viewer shall read current application status from `application_details.json`.

11.3.2. The Application Viewer shall normalize equivalent status values.

11.3.3. The Application Viewer shall allow valid status transitions from `Ongoing` to `Completed`.

11.3.4. The Application Viewer shall allow valid status transitions from `Completed` to `Close`.

11.3.5. The Application Viewer shall update `application_details.json` when status changes.

11.3.6. The Application Viewer shall rename the application folder to reflect the updated status when possible.

11.3.7. When marking an application completed, the system shall support capturing whether the application was submitted and the submission date.

## 12. Error Handling And Resilience

### 12.1 Model Errors

12.1.1. The system shall show a user-visible error when model streaming fails.

12.1.2. The system shall store the error message in the relevant result area when generation fails.

12.1.3. The system shall prevent metadata extraction from proceeding when no active model is available.

### 12.2 File System Errors

12.2.1. The system shall show a user-visible error when application folder creation fails.

12.2.2. The system shall write diagnostic logs for custom resume generation and compilation failures.

12.2.3. The system shall continue creating available artifacts when optional artifacts cannot be produced.

### 12.3 Resume Processing Errors

12.3.1. The system shall show a warning when resume text extraction fails.

12.3.2. The system shall show a warning when resume vector index creation fails.

12.3.3. The system shall skip resume context rather than failing the full analysis when resume vector search is unavailable.

## 13. Data And Privacy

### 13.1 Local Data Handling

13.1.1. The system shall store generated application artifacts locally in user-selected folders.

13.1.2. The system shall store user profile settings locally.

13.1.3. The system shall store resume vector indexes locally inside the POC directory.

13.1.4. The system shall not upload generated application folders to any third-party storage service as part of the POC workflow.

### 13.2 Provider Data Exposure

13.2.1. The system shall send job description text to the selected LLM provider during generation.

13.2.2. The system shall send relevant resume excerpts to the selected LLM provider when resume context is included.

13.2.3. The system shall send long-form resume text to the selected LLM provider during custom resume generation.

13.2.4. The system shall keep provider API keys out of generated documents and application folders.

## 14. Non-Functional Requirements

### 14.1 Usability

14.1.1. The system shall organize the POC into separate pages for analysis, resume viewing, settings, and application viewing.

14.1.2. The system shall expose common actions through visible Streamlit controls.

14.1.3. The system shall provide progress indicators during slow model and file-generation operations.

### 14.2 Performance

14.2.1. The system shall cache generated analysis results during a session to avoid unnecessary repeated model calls.

14.2.2. The system shall avoid rebuilding the resume vector index when the same uploaded file is already indexed during the session.

14.2.3. The system shall limit resume retrieval to a configurable top-k number of chunks.

### 14.3 Portability

14.3.1. The system shall support WSL path conversion for Windows folder selection and configured Windows file paths.

14.3.2. The system shall use Windows-compatible sanitization for generated file and folder names.

14.3.3. The system shall degrade gracefully when Windows-specific folder browsing is unavailable.

### 14.4 Maintainability

14.4.1. The system shall keep product-specific POC code under `implementations/job-description-analyzer`.

14.4.2. The system may reuse shared LLM and utility code from `src`.

14.4.3. The system shall keep prompt construction separate from UI rendering where practical.

14.4.4. The system shall keep application folder creation logic separate from analysis rendering logic where practical.

## 15. Out Of Scope

### 15.1 Excluded Capabilities

15.1.1. The POC shall not automatically submit applications to job boards or applicant tracking systems.

15.1.2. The POC shall not manage recruiter communications.

15.1.3. The POC shall not provide multi-user authentication or authorization.

15.1.4. The POC shall not provide cloud synchronization beyond the user's local file system or OneDrive folder behavior.

15.1.5. The POC shall not guarantee that generated content is factually correct without user review.

15.1.6. The POC shall not guarantee that generated LaTeX compiles when no LaTeX engine is installed or when the model emits invalid LaTeX.
