# CareerAgent API Specification

Status: draft for POC extraction  
API style: REST over HTTPS with OpenAPI 3.1-compatible schemas  
Base path: `/api/v1`

This document describes how the current CareerAgent POC could be exposed as an API instead of being implemented through local Streamlit functions. The API preserves the current product behaviors: job description analysis, resume-aware RAG, cover letter generation, profile settings, model selection, and creation of an application package containing source metadata and generated documents.

## Design Goals

- Keep the UI thin: the frontend submits job descriptions, profile data, resume files, and generation requests.
- Keep model and embedding provider details server-side.
- Support both one-shot and streaming LLM responses.
- Make generated outputs reusable: analysis text can later be exported into `.docx` files or bundled into an application package.
- Make resume context explicit so the client can show whether an answer used resume excerpts.

## Authentication

All endpoints require bearer-token authentication unless marked public.

```http
Authorization: Bearer <access_token>
```

The POC can start with a single local token. A production version should issue user-scoped tokens and isolate resumes, profiles, generated analyses, and application packages per user.

## Common Types

### Tool Ids

CareerAgent supports these analysis tools:

```yaml
AnalysisToolId:
  type: string
  enum:
    - summary
    - requirements
    - tech_stack
    - red_flags
    - interview_prep
    - cover_letter
    - compensation
```

### Analysis Result

```yaml
AnalysisResult:
  type: object
  required:
    - id
    - tool_id
    - content
    - model_id
    - used_resume_context
    - created_at
  properties:
    id:
      type: string
      format: uuid
    tool_id:
      $ref: "#/components/schemas/AnalysisToolId"
    content:
      type: string
      description: Markdown content generated for display or export.
    model_id:
      type: string
      example: gpt-4.1-mini
    used_resume_context:
      type: boolean
    resume_context:
      type: array
      items:
        $ref: "#/components/schemas/ResumeExcerpt"
    created_at:
      type: string
      format: date-time
```

### Resume Excerpt

```yaml
ResumeExcerpt:
  type: object
  required:
    - rank
    - text
  properties:
    rank:
      type: integer
      minimum: 1
    score:
      type: number
      format: float
      nullable: true
    text:
      type: string
```

### Error Response

```yaml
ErrorResponse:
  type: object
  required:
    - error
  properties:
    error:
      type: object
      required:
        - code
        - message
      properties:
        code:
          type: string
          example: validation_error
        message:
          type: string
        details:
          type: object
          additionalProperties: true
```

## OpenAPI Draft

```yaml
openapi: 3.1.0
info:
  title: CareerAgent API
  version: 0.1.0
  description: API surface for the CareerAgent job description analyzer POC.
servers:
  - url: https://careeragent.example.com/api/v1
security:
  - bearerAuth: []

paths:
  /health:
    get:
      summary: Health check
      security: []
      responses:
        "200":
          description: API is available
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: ok

  /models:
    get:
      summary: List available generation models
      description: Returns server-configured models that can be used for analysis requests.
      responses:
        "200":
          description: Available models
          content:
            application/json:
              schema:
                type: object
                required: [models]
                properties:
                  models:
                    type: array
                    items:
                      $ref: "#/components/schemas/Model"

  /profile:
    get:
      summary: Get the current user profile
      responses:
        "200":
          description: Current profile values
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/UserProfile"
    put:
      summary: Upsert the current user profile
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/UserProfile"
      responses:
        "200":
          description: Saved profile
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/UserProfile"

  /resumes:
    post:
      summary: Upload and index a resume
      description: Accepts a `.docx` resume, extracts text, chunks it, embeds it, and stores a vector index for later analysis calls.
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required: [file]
              properties:
                file:
                  type: string
                  format: binary
      responses:
        "201":
          description: Resume indexed
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Resume"
        "400":
          $ref: "#/components/responses/BadRequest"
    get:
      summary: List indexed resumes
      responses:
        "200":
          description: Resumes
          content:
            application/json:
              schema:
                type: object
                required: [resumes]
                properties:
                  resumes:
                    type: array
                    items:
                      $ref: "#/components/schemas/Resume"

  /resumes/{resume_id}:
    get:
      summary: Get resume metadata and extracted text
      parameters:
        - $ref: "#/components/parameters/ResumeId"
      responses:
        "200":
          description: Resume detail
          content:
            application/json:
              schema:
                allOf:
                  - $ref: "#/components/schemas/Resume"
                  - type: object
                    properties:
                      extracted_text:
                        type: string
    delete:
      summary: Delete an indexed resume
      parameters:
        - $ref: "#/components/parameters/ResumeId"
      responses:
        "204":
          description: Deleted

  /resumes/{resume_id}/query:
    post:
      summary: Query resume context
      description: Returns top matching resume excerpts for a job description or custom question.
      parameters:
        - $ref: "#/components/parameters/ResumeId"
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [query]
              properties:
                query:
                  type: string
                top_k:
                  type: integer
                  minimum: 1
                  maximum: 20
                  default: 5
      responses:
        "200":
          description: Matching excerpts
          content:
            application/json:
              schema:
                type: object
                required: [resume_id, excerpts]
                properties:
                  resume_id:
                    type: string
                    format: uuid
                  excerpts:
                    type: array
                    items:
                      $ref: "#/components/schemas/ResumeExcerpt"

  /job-descriptions/extract-metadata:
    post:
      summary: Extract application metadata from a job description
      description: Extracts title, company, posting date, and source URL if present. If no posting date is found, the API may return today's date with `date_inferred=true`.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/JobDescriptionMetadataRequest"
      responses:
        "200":
          description: Extracted metadata
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ApplicationMetadata"

  /analyses:
    post:
      summary: Generate a job description analysis
      description: Runs one CareerAgent analysis tool against a pasted job description, optionally enriched with resume excerpts.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CreateAnalysisRequest"
      responses:
        "201":
          description: Generated analysis
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/AnalysisResult"
        "400":
          $ref: "#/components/responses/BadRequest"

  /analyses/stream:
    post:
      summary: Stream a job description analysis
      description: Streams generated Markdown chunks as server-sent events.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CreateAnalysisRequest"
      responses:
        "200":
          description: SSE stream of generation events
          content:
            text/event-stream:
              schema:
                type: string

  /questions:
    post:
      summary: Ask a custom question about a job description
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/AskQuestionRequest"
      responses:
        "201":
          description: Generated answer
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/QuestionResult"

  /cover-letter/envelope:
    post:
      summary: Build cover letter header and footer
      description: Produces deterministic sender, contact, Re line, and signature text from profile plus job metadata. The model should only generate the body.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [profile, title, company]
              properties:
                profile:
                  $ref: "#/components/schemas/UserProfile"
                title:
                  type: string
                company:
                  type: string
      responses:
        "200":
          description: Envelope text
          content:
            application/json:
              schema:
                type: object
                required: [header, footer]
                properties:
                  header:
                    type: string
                  footer:
                    type: string

  /documents:
    post:
      summary: Render generated content as a document
      description: Converts Markdown-like analysis output into a `.docx` document.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CreateDocumentRequest"
      responses:
        "201":
          description: Document created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Document"

  /applications:
    post:
      summary: Create an application package
      description: Creates a server-side application package from job metadata, original job description, selected analyses, generated documents, and optional resume template.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CreateApplicationRequest"
      responses:
        "201":
          description: Application package created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ApplicationPackage"

  /applications/{application_id}:
    get:
      summary: Get application package metadata
      parameters:
        - $ref: "#/components/parameters/ApplicationId"
      responses:
        "200":
          description: Application package
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ApplicationPackage"

  /applications/{application_id}/archive:
    get:
      summary: Download an application package archive
      parameters:
        - $ref: "#/components/parameters/ApplicationId"
      responses:
        "200":
          description: Zip archive
          content:
            application/zip:
              schema:
                type: string
                format: binary

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer

  parameters:
    ResumeId:
      name: resume_id
      in: path
      required: true
      schema:
        type: string
        format: uuid
    ApplicationId:
      name: application_id
      in: path
      required: true
      schema:
        type: string
        format: uuid

  responses:
    BadRequest:
      description: Invalid request
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/ErrorResponse"

  schemas:
    AnalysisToolId:
      type: string
      enum:
        - summary
        - requirements
        - tech_stack
        - red_flags
        - interview_prep
        - cover_letter
        - compensation

    Model:
      type: object
      required: [id, display_name, provider, capabilities, token_limits]
      properties:
        id:
          type: string
          example: gpt-4.1-mini
        display_name:
          type: string
        provider:
          type: string
          enum: [openai, cohere]
        capabilities:
          type: array
          items:
            type: string
            enum: [chat, chat_streaming]
        token_limits:
          type: object
          required: [context_window, max_output_tokens]
          properties:
            context_window:
              type: integer
            max_output_tokens:
              type: integer

    UserProfile:
      type: object
      properties:
        name:
          type: string
        email:
          type: string
          format: email
        phone:
          type: string
        linkedin:
          type: string
        github:
          type: string

    Resume:
      type: object
      required: [id, filename, chunk_count, fingerprint, created_at]
      properties:
        id:
          type: string
          format: uuid
        filename:
          type: string
        chunk_count:
          type: integer
        fingerprint:
          type: string
          description: Changes when the indexed resume content changes.
        created_at:
          type: string
          format: date-time

    ResumeExcerpt:
      type: object
      required: [rank, text]
      properties:
        rank:
          type: integer
          minimum: 1
        score:
          type: number
          format: float
          nullable: true
        text:
          type: string

    JobDescriptionMetadataRequest:
      type: object
      required: [job_description]
      properties:
        job_description:
          type: string
        model_id:
          type: string

    ApplicationMetadata:
      type: object
      required: [title, company, posted_on, status]
      properties:
        title:
          type: string
        company:
          type: string
        posted_on:
          type: string
          format: date
        date_inferred:
          type: boolean
          default: false
        status:
          type: string
          enum: [Ongoing, Completed, Close]
          default: Ongoing
        source_url:
          type: string
          format: uri
          nullable: true

    CreateAnalysisRequest:
      type: object
      required: [tool_id, job_description]
      properties:
        tool_id:
          $ref: "#/components/schemas/AnalysisToolId"
        job_description:
          type: string
        model_id:
          type: string
        resume_id:
          type: string
          format: uuid
          nullable: true
        include_resume_context:
          type: boolean
          default: true
        top_k:
          type: integer
          minimum: 1
          maximum: 20
          default: 5
        profile:
          $ref: "#/components/schemas/UserProfile"
        metadata:
          $ref: "#/components/schemas/ApplicationMetadata"

    AnalysisResult:
      type: object
      required: [id, tool_id, content, model_id, used_resume_context, created_at]
      properties:
        id:
          type: string
          format: uuid
        tool_id:
          $ref: "#/components/schemas/AnalysisToolId"
        content:
          type: string
        model_id:
          type: string
        used_resume_context:
          type: boolean
        resume_context:
          type: array
          items:
            $ref: "#/components/schemas/ResumeExcerpt"
        created_at:
          type: string
          format: date-time

    AskQuestionRequest:
      type: object
      required: [job_description, question]
      properties:
        job_description:
          type: string
        question:
          type: string
        model_id:
          type: string
        resume_id:
          type: string
          format: uuid
          nullable: true
        include_resume_context:
          type: boolean
          default: true

    QuestionResult:
      type: object
      required: [id, question, answer, model_id, used_resume_context, created_at]
      properties:
        id:
          type: string
          format: uuid
        question:
          type: string
        answer:
          type: string
        model_id:
          type: string
        used_resume_context:
          type: boolean
        resume_context:
          type: array
          items:
            $ref: "#/components/schemas/ResumeExcerpt"
        created_at:
          type: string
          format: date-time

    CreateDocumentRequest:
      type: object
      required: [content, format]
      properties:
        title:
          type: string
        filename:
          type: string
        content:
          type: string
          description: Markdown-like text with support for bold and italic runs.
        format:
          type: string
          enum: [docx]

    Document:
      type: object
      required: [id, filename, format, download_url, created_at]
      properties:
        id:
          type: string
          format: uuid
        filename:
          type: string
        format:
          type: string
          enum: [docx]
        download_url:
          type: string
          format: uri
        created_at:
          type: string
          format: date-time

    CreateApplicationRequest:
      type: object
      required: [job_description, metadata]
      properties:
        job_description:
          type: string
        metadata:
          $ref: "#/components/schemas/ApplicationMetadata"
        analysis_ids:
          type: array
          items:
            type: string
            format: uuid
        include_latex_template:
          type: boolean
          default: true

    ApplicationPackage:
      type: object
      required: [id, folder_name, metadata, files, created_at]
      properties:
        id:
          type: string
          format: uuid
        folder_name:
          type: string
          example: Senior Developer - Example Corp - Ongoing - 2026-06-04
        metadata:
          $ref: "#/components/schemas/ApplicationMetadata"
        files:
          type: array
          items:
            type: object
            required: [filename, content_type, download_url]
            properties:
              filename:
                type: string
              content_type:
                type: string
              download_url:
                type: string
                format: uri
        archive_url:
          type: string
          format: uri
        created_at:
          type: string
          format: date-time

    ErrorResponse:
      type: object
      required: [error]
      properties:
        error:
          type: object
          required: [code, message]
          properties:
            code:
              type: string
            message:
              type: string
            details:
              type: object
              additionalProperties: true
```

## Streaming Events

`POST /analyses/stream` uses server-sent events. Events are newline-delimited SSE messages:

```text
event: metadata
data: {"analysis_id":"...","tool_id":"cover_letter","model_id":"gpt-4.1-mini","used_resume_context":true}

event: chunk
data: {"text":"Dear Hiring Manager,\n\n"}

event: chunk
data: {"text":"I am excited to apply..."}

event: done
data: {"analysis_id":"..."}
```

Error event:

```text
event: error
data: {"code":"model_error","message":"The model provider returned an error."}
```

## Endpoint Notes

### `POST /analyses`

This endpoint replaces the local `TOOLS` prompt functions and `_stream_into_placeholder` flow. The server should:

1. Validate the selected `tool_id`.
2. Load or accept profile data when `tool_id=cover_letter`.
3. Retrieve resume context when `resume_id` and `include_resume_context=true`.
4. Build the same task-specific prompt currently used by the POC.
5. Call the selected model.
6. Return Markdown content plus metadata about the model and resume context.

For `cover_letter`, the response content should include the deterministic envelope plus generated body, matching the current behavior where the model writes only the body.

### `POST /job-descriptions/extract-metadata`

This endpoint replaces the local metadata extraction used before creating an application folder. It should extract:

- `title`
- `company`
- `posted_on`
- `source_url`, when a URL is present in the submitted text

If the model cannot find a posting date, the API may set `posted_on` to the request date and return `date_inferred=true`.

### `POST /applications`

This endpoint replaces local folder creation. A production API should not write directly to a user-selected desktop path. Instead, it should create a server-side package with downloadable files:

- `original_description.txt`
- `application_details.json`
- generated `.docx` analysis files
- optional LaTeX resume template
- optional zip archive

The client can then download the archive or individual files.

## Example Requests

### Generate Requirements Analysis

```http
POST /api/v1/analyses
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{
  "tool_id": "requirements",
  "job_description": "Senior Python Developer...",
  "model_id": "gpt-4.1-mini",
  "resume_id": "5bd04d86-f54c-4e3a-93ec-31e2b0b647a4",
  "include_resume_context": true,
  "top_k": 5
}
```

### Generate Cover Letter

```json
{
  "tool_id": "cover_letter",
  "job_description": "Senior Python Developer...",
  "model_id": "gpt-4.1-mini",
  "resume_id": "5bd04d86-f54c-4e3a-93ec-31e2b0b647a4",
  "profile": {
    "name": "Jane Applicant",
    "email": "jane@example.com",
    "phone": "+14165550123",
    "linkedin": "https://www.linkedin.com/in/jane",
    "github": "https://github.com/jane"
  },
  "metadata": {
    "title": "Senior Python Developer",
    "company": "Example Corp",
    "posted_on": "2026-06-04",
    "status": "Ongoing"
  }
}
```

### Create Application Package

```json
{
  "job_description": "Senior Python Developer...",
  "metadata": {
    "title": "Senior Python Developer",
    "company": "Example Corp",
    "posted_on": "2026-06-04",
    "status": "Ongoing",
    "source_url": "https://www.linkedin.com/jobs/view/example"
  },
  "analysis_ids": [
    "514c3f9d-137c-40fd-8321-aea69d5f884c",
    "8d06d8ac-b238-4064-83a8-fd5f0378b4d9"
  ],
  "include_latex_template": true
}
```

## Non-Goals For The POC API

- Multi-tenant billing and subscription management.
- Full applicant tracking system workflows.
- Direct submission to LinkedIn, Workday, Greenhouse, Lever, or other job boards.
- Browser automation for job applications.
- Long-term document version history.

## Implementation Considerations

- Store raw resumes and vector indexes per user. Never share resume context across users.
- Keep provider API keys on the server. Clients should only reference `model_id`.
- Use asynchronous jobs for large document exports or package creation if generation becomes slow.
- Apply rate limits to generation endpoints.
- Log model/provider errors without logging sensitive resume text unless explicit debug logging is enabled.
- Treat generated documents as private user data and use short-lived signed download URLs.
