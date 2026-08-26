<script lang="ts">
  import { createAboutSections } from './about-content';

  export let portraitUrl: string;
  export let softwareResumeUrl: string;
  export let projectsUrl: string;
  export let musicResumeUrl: string;
  export let musicVideoUrl: string;
  export let pickleballArticleUrl: string;
  export let chessProfileUrl: string;

  let openSectionIds = new Set<string>();

  $: sections = createAboutSections({
    portraitUrl,
    softwareResumeUrl,
    projectsUrl,
    musicResumeUrl,
    musicVideoUrl,
    pickleballArticleUrl,
    chessProfileUrl,
  });
  $: intro = sections[0];
  $: interests = sections.slice(1);

  const toggleSection = (sectionId: string) => {
    const nextOpenSectionIds = new Set(openSectionIds);

    if (nextOpenSectionIds.has(sectionId)) nextOpenSectionIds.delete(sectionId);
    else nextOpenSectionIds.add(sectionId);

    openSectionIds = nextOpenSectionIds;
  };
</script>

<div class="page-scroll-installation about-scroll-installation">
  <div
    class="page-scroll-hanging about-scroll-hanging"
    aria-label="About Cyrus Asasi"
  >
    <article
      class="page-scroll-paper about-scroll-paper"
      aria-labelledby="about-scroll-title"
    >
      <div
        class="page-scroll-paper__roll page-scroll-paper__roll--top about-scroll-paper__roll about-scroll-paper__roll--top"
        aria-hidden="true"
      ></div>

      <div class="page-scroll-paper__sheet about-scroll-paper__sheet">
        <div
          class="page-scroll-paper__viewport about-scroll-paper__viewport"
          aria-label="About content"
        >
          <header class="page-scroll-header about-scroll-header">
            <h1 id="about-scroll-title">About</h1>
            <div
              class="page-scroll-header__rule about-scroll-header__rule"
              aria-hidden="true"
            ></div>
          </header>

          {#if intro?.portrait}
            <figure class="about-scroll-portrait-wrap">
              <span class="about-scroll-portrait-frame" aria-hidden="true">
                <span class="about-scroll-portrait-glass">
                  <img
                    class="about-scroll-portrait"
                    src={intro.portrait.src}
                    alt=""
                    width="480"
                    height="480"
                    decoding="async"
                  />
                  <span class="about-scroll-portrait-shade"></span>
                  <span class="about-scroll-portrait-reflection"></span>
                </span>
                <span class="about-scroll-portrait-sill"></span>
              </span>
              <span class="visually-hidden">{intro.portrait.alt}</span>
            </figure>
          {/if}

          {#if intro}
            <div class="about-scroll-intro">
              {#each intro.paragraphs as paragraph, index}
                <p class={index === 0 ? 'about-scroll-intro__lead' : undefined}>
                  {paragraph}
                </p>
              {/each}
            </div>
          {/if}

          <div class="about-scroll-rule" aria-hidden="true"></div>

          <div class="about-scroll-sections" aria-label="Interests">
            {#each interests as channel}
              {@const isOpen = openSectionIds.has(channel.id)}
              <section class="about-scroll-section" class:is-open={isOpen}>
                <button
                  type="button"
                  class="about-scroll-section__toggle"
                  aria-expanded={isOpen}
                  aria-controls={`about-section-${channel.id}`}
                  onclick={() => toggleSection(channel.id)}
                >
                  <span>{channel.label}</span>
                  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="m8 4 8 8-8 8" />
                  </svg>
                </button>

                <div
                  id={`about-section-${channel.id}`}
                  class="about-scroll-section__panel"
                  aria-hidden={!isOpen}
                >
                  <div class="about-scroll-section__content">
                    <div class="about-scroll-section__body">
                      {#each channel.paragraphs as paragraph}
                        <p>{paragraph}</p>
                      {/each}

                      {#if channel.links?.length}
                        <nav
                          class="about-scroll-section__links"
                          aria-label={`${channel.label} links`}
                        >
                          {#each channel.links as link}
                            <a
                              href={link.href}
                              target={link.external ? '_blank' : undefined}
                              rel={link.external
                                ? 'noopener noreferrer'
                                : undefined}
                              tabindex={isOpen ? undefined : -1}
                            >
                              <span>{link.label}</span>
                              <svg
                                viewBox="0 0 16 16"
                                aria-hidden="true"
                                focusable="false"
                              >
                                {#if link.external}
                                  <path d="M4 12 12 4M6.25 4H12v5.75" />
                                {:else}
                                  <path d="M2.5 8h10.5M9 4l4 4-4 4" />
                                {/if}
                              </svg>
                            </a>
                          {/each}
                        </nav>
                      {/if}
                    </div>
                  </div>
                </div>
              </section>
            {/each}
          </div>
        </div>
      </div>

      <div
        class="page-scroll-paper__roll page-scroll-paper__roll--bottom about-scroll-paper__roll about-scroll-paper__roll--bottom"
        aria-hidden="true"
      ></div>
    </article>
  </div>
</div>
