<script lang="ts">
  import { onDestroy } from 'svelte';
  import { createAboutTVChannels } from './about-tv-content';

  export let portraitUrl: string;
  export let softwareResumeUrl: string;
  export let projectsUrl: string;
  export let musicResumeUrl: string;
  export let musicVideoUrl: string;
  export let pickleballArticleUrl: string;
  export let chessProfileUrl: string;

  let openSectionIds = new Set<string>();
  let accordionScrollFrame: number | null = null;

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

  const cancelAccordionScroll = () => {
    if (accordionScrollFrame !== null) {
      window.cancelAnimationFrame(accordionScrollFrame);
      accordionScrollFrame = null;
    }
  };

  const followOpeningSection = (button: HTMLButtonElement, sectionId: string) => {
    cancelAccordionScroll();

    const section = button.closest<HTMLElement>('.about-scroll-section');
    const viewport = button.closest<HTMLElement>('.about-scroll-paper__viewport');
    if (!section || !viewport) return;

    const startScrollTop = viewport.scrollTop;
    const topBreathingRoom = 18;
    const animationDuration = 760;
    const startedAt = performance.now();

    const follow = (now: number) => {
      if (!openSectionIds.has(sectionId)) {
        accordionScrollFrame = null;
        return;
      }

      // While the accordion is physically getting taller, the viewport's
      // maximum scroll position is also growing. Follow that growing range on
      // every animation frame instead of asking the browser to scroll before
      // there is anywhere to scroll to. This makes the page begin moving as
      // soon as the first pixels of the panel open and keeps the motion coupled
      // to the accordion animation.
      const viewportRect = viewport.getBoundingClientRect();
      const sectionRect = section.getBoundingClientRect();
      const sectionTop = viewport.scrollTop + sectionRect.top - viewportRect.top;
      const requestedTop = Math.max(startScrollTop, sectionTop - topBreathingRoom);
      const maxScrollTop = Math.max(0, viewport.scrollHeight - viewport.clientHeight);
      const availableTarget = Math.min(requestedTop, maxScrollTop);

      if (availableTarget > viewport.scrollTop) {
        viewport.scrollTop = availableTarget;
      }

      if (now - startedAt < animationDuration) {
        accordionScrollFrame = window.requestAnimationFrame(follow);
        return;
      }

      // One final native smooth scroll catches the last few pixels if layout or
      // font metrics changed during the expansion. In the normal case this is
      // already at the target and is effectively a no-op.
      const finalViewportRect = viewport.getBoundingClientRect();
      const finalSectionRect = section.getBoundingClientRect();
      const finalSectionTop = viewport.scrollTop + finalSectionRect.top - finalViewportRect.top;
      const finalTarget = Math.max(startScrollTop, finalSectionTop - topBreathingRoom);
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      viewport.scrollTo({
        top: finalTarget,
        behavior: prefersReducedMotion ? 'auto' : 'smooth',
      });
      accordionScrollFrame = null;
    };

    accordionScrollFrame = window.requestAnimationFrame(follow);
  };

  const toggleSection = (event: MouseEvent, sectionId: string) => {
    const button = event.currentTarget as HTMLButtonElement;
    const opening = !openSectionIds.has(sectionId);
    const nextOpenSectionIds = new Set(openSectionIds);

    if (opening) nextOpenSectionIds.add(sectionId);
    else nextOpenSectionIds.delete(sectionId);

    openSectionIds = nextOpenSectionIds;

    if (opening) {
      followOpeningSection(button, sectionId);
    } else {
      cancelAccordionScroll();
    }
  };

  onDestroy(cancelAccordionScroll);
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
              {@const isOpen = openSectionIds.has(channel.id)}
              <section class="about-scroll-section" class:is-open={isOpen}>
                <button
                  type="button"
                  class="about-scroll-section__toggle"
                  aria-expanded={isOpen}
                  aria-controls={`about-section-${channel.id}`}
                  onclick={(event) => toggleSection(event, channel.id)}
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
                        <nav class="about-scroll-section__links" aria-label={`${channel.label} links`}>
                          {#each channel.links as link}
                            <a
                              href={link.href}
                              target={link.external ? '_blank' : undefined}
                              rel={link.external ? 'noopener noreferrer' : undefined}
                              tabindex={isOpen ? undefined : -1}
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
                </div>
              </section>
            {/each}
          </div>
        </div>
      </div>

      <div class="about-scroll-paper__roll about-scroll-paper__roll--bottom" aria-hidden="true"></div>
    </article>
  </div>
</div>
