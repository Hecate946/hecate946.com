<script lang="ts">
  import type { AboutTVChannel } from './about-tv-content';

  export let channel: AboutTVChannel;
</script>

<article class="about-tv-channel">
  <div class="about-tv-channel__body">
    <header class="about-tv-channel__header">
      <div class="about-tv-channel__heading-copy">
        <h1>{channel.title}</h1>

        {#if channel.subtitle}
          <p class="about-tv-channel__subtitle">{channel.subtitle}</p>
        {/if}
      </div>

      {#if channel.portrait}
        <figure class="about-tv-channel__portrait-wrap">
          <img
            class="about-tv-channel__portrait"
            src={channel.portrait.src}
            alt={channel.portrait.alt}
            width="480"
            height="480"
            decoding="async"
          />
        </figure>
      {/if}
    </header>

    <div class="about-tv-channel__story">
      {#each channel.paragraphs as paragraph}
        <p class="about-tv-channel__paragraph">{paragraph}</p>
      {/each}

      {#if channel.links?.length}
        <nav class="about-tv-channel__links" aria-label={`${channel.label} links`}>
          {#each channel.links as link}
            <a
              href={link.href}
              target={link.external ? '_blank' : undefined}
              rel={link.external ? 'noopener noreferrer' : undefined}
              onpointerdown={(event) => event.stopPropagation()}
              onclick={(event) => event.stopPropagation()}
            >
              {link.label}
              <svg class="about-tv-channel__link-arrow" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
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
</article>
