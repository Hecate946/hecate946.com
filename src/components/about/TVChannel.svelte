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
              {link.label}<span aria-hidden="true">{link.external ? ' ↗' : ' →'}</span>
            </a>
          {/each}
        </nav>
      {/if}
    </div>
  </div>
</article>
