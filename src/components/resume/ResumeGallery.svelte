<script lang="ts">
  interface ResumeItem {
    id: string;
    number: string;
    label: string;
    shortLabel: string;
    pdfUrl: string;
    previewUrl: string;
    previewSrcset: string;
    previewWidth: number;
    previewHeight: number;
  }

  export let resumes: readonly ResumeItem[];
</script>

<div class="resume-gallery" aria-label="Resumes">
  {#each resumes as resume (resume.id)}
    <a
      class="resume-frame"
      href={resume.pdfUrl}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Open ${resume.label} resume in the browser PDF viewer`}
    >
      <span class="resume-frame__recess" aria-hidden="true">
        <span class="resume-frame__glass">
          <img
            class="resume-frame__preview"
            src={resume.previewUrl}
            srcset={resume.previewSrcset}
            sizes="(max-width: 48rem) min(88vw, 38rem), min(42vw, 34rem)"
            alt=""
            width={resume.previewWidth}
            height={resume.previewHeight}
            loading="eager"
            decoding="async"
            draggable="false"
          />
        </span>
        <span class="resume-frame__reflection"></span>
      </span>

      <span class="resume-frame__sill" aria-hidden="true"></span>

      <span class="resume-frame__label">
        <span class="resume-frame__index">{resume.number}</span>
        <span class="resume-frame__name">{resume.shortLabel}</span>
        <span class="resume-frame__arrow" aria-hidden="true">
          <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
            <path d="M4 12 12 4M6.25 4H12v5.75" />
          </svg>
        </span>
      </span>
    </a>
  {/each}
</div>
