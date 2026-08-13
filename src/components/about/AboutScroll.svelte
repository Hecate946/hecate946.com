<script lang="ts">
  import { createAboutTVChannels } from './about-tv-content';

  export let portraitUrl: string;
  export let softwareResumeUrl: string;
  export let projectsUrl: string;
  export let musicResumeUrl: string;
  export let musicVideoUrl: string;
  export let pickleballArticleUrl: string;
  export let chessProfileUrl: string;

  $: channels = createAboutTVChannels({
    portraitUrl,
    softwareResumeUrl,
    projectsUrl,
    musicResumeUrl,
    musicVideoUrl,
    pickleballArticleUrl,
    chessProfileUrl,
  });
  $: intro = channels[0];
  $: interests = channels.slice(1);
</script>

<div class="about-scroll-installation">
  <div class="about-scroll-hanging" aria-label="About Cyrus Asasi">
    <article class="about-scroll-paper" aria-labelledby="about-scroll-title">
      <div class="about-scroll-paper__roll about-scroll-paper__roll--top" aria-hidden="true"></div>

      <div class="about-scroll-paper__sheet">
        <div class="about-scroll-paper__viewport">
          <header class="about-scroll-header">
            <h1 id="about-scroll-title">About</h1>
            <div class="about-scroll-header__rule" aria-hidden="true"></div>

            {#if intro?.portrait}
              <figure class="about-scroll-portrait-wrap">
                <img
                  class="about-scroll-portrait"
                  src={intro.portrait.src}
                  alt={intro.portrait.alt}
                  width="480"
                  height="480"
                  decoding="async"
                />
              </figure>
            {/if}
          </header>

          {#if intro}
            <div class="about-scroll-intro">
              {#each intro.paragraphs as paragraph, index}
                <p class={index === 0 ? 'about-scroll-intro__lead' : undefined}>{paragraph}</p>
              {/each}
            </div>
          {/if}

          <div class="about-scroll-sections" aria-label="Interests">
            {#each interests as channel}
              <details class="about-scroll-section">
                <summary>
                  <span>{channel.label}</span>
                  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="m8 4 8 8-8 8" />
                  </svg>
                </summary>

                <div class="about-scroll-section__panel">
                  <div class="about-scroll-section__content">
                    {#each channel.paragraphs as paragraph}
                      <p>{paragraph}</p>
                    {/each}

                    {#if channel.links?.length}
                      <nav class="about-scroll-section__links" aria-label={`${channel.label} links`}>
                        {#each channel.links as link}
                          <a
                            href={link.href}
                            target={link.external ? '_blank' : undefined}
                            rel={link.external ? 'noopener noreferrer' : undefined}
                          >
                            <span>{link.label}</span>
                            <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
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
              </details>
            {/each}
          </div>
        </div>
      </div>

      <div class="about-scroll-paper__roll about-scroll-paper__roll--bottom" aria-hidden="true"></div>
    </article>
  </div>
</div>
