<script lang="ts">
  import WebGLBook from './WebGLBook.svelte';
  import type { BookSpread } from './book-types';

  export let musicVideoUrl: string;
  export let pickleballArticleUrl: string;
  export let chessProfileUrl: string;
  export let resumesUrl: string;
  export let portraitUrl: string;
  export let softwareImageUrl: string;
  export let musicImageUrl: string;
  export let pickleballImageUrl: string;

  const spreads: BookSpread[] = [
    {
      id: 'about',
      label: 'About',
      eyebrow: 'ABOUT',
      title: 'Cyrus Asasi',
      paragraphs: [
        "I split most of my time between code and music. I studied computer science and clarinet performance at UCLA, and I'm back there now for a master's in clarinet.",
        "I tend to get obsessed with things that are hard to get exactly right: taking apart strange systems, building something for the web, learning a difficult piece, or chasing a tiny detail until it finally feels right.",
      ],
      visual: {
        src: portraitUrl,
        alt: 'Portrait of Cyrus Asasi',
        caption: 'Los Angeles, California',
        mode: 'portrait',
      },
    },
    {
      id: 'software',
      label: 'Software',
      eyebrow: 'SOFTWARE',
      title: 'I like taking things apart',
      paragraphs: [
        "I've always liked figuring out how things work. A lot of my work has involved reverse engineering: digging through a system until it makes sense, then rebuilding the useful parts more cleanly.",
        "Most of my side projects start the same way: something bothers me, I wonder if I can make it better, and I lose a few evenings to it.",
      ],
      visual: {
        src: softwareImageUrl,
        alt: 'A software project from Cyrus Asasi',
        caption: 'Selected software work',
        mode: 'screen',
      },
      link: {
        href: resumesUrl,
        label: 'View resumes',
      },
    },
    {
      id: 'music',
      label: 'Music',
      eyebrow: 'MUSIC',
      title: 'Music has always been there',
      paragraphs: [
        "Clarinet has been the constant for most of my life. I'm currently doing my master's at UCLA, where I also did my undergraduate music degree alongside computer science.",
        "In 2026 I got to solo with the UCLA Philharmonia after winning the All-Stars Competition. I also play piano, mostly because I love chamber music. I listen to an unreasonable amount of Brahms, Ravel, and Kapustin.",
      ],
      visual: {
        src: musicImageUrl,
        alt: 'Clarinet performance résumé for Cyrus Asasi',
        caption: 'Clarinet performance — selected experience',
        mode: 'document',
      },
      link: {
        href: musicVideoUrl,
        label: 'Watch a performance',
        external: true,
      },
    },
    {
      id: 'interests',
      label: 'Elsewhere',
      eyebrow: 'ELSEWHERE',
      title: 'Away from the desk',
      visual: {
        src: pickleballImageUrl,
        alt: 'UCLA Pickleball at the California Collegiate Super Regional',
        caption: 'California Collegiate Super Regional',
        mode: 'photo',
      },
      interests: [
        {
          title: 'Pickleball',
          body: "Pickleball started as something casual and got a little out of hand. I play around the 5.0 level and captain UCLA's team. Winning the California Collegiate Super Regional is still one of my favorite team memories.",
          link: {
            href: pickleballArticleUrl,
            label: 'Tournament recap',
            external: true,
          },
        },
        {
          title: 'Chess',
          body: 'Chess was my first serious obsession. I started in middle school and eventually hit 2450 online. I play less now, but I still love the calculation and pattern recognition that made me stick with it in the first place.',
          link: {
            href: chessProfileUrl,
            label: 'Chess.com profile',
            external: true,
          },
        },
      ],
    },
  ];
</script>

<section class="about-page-turner" aria-label="About Cyrus Asasi">
  <WebGLBook {spreads} />
</section>
