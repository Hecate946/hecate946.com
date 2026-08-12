<script lang="ts">
  import WebGLBook from './WebGLBook.svelte';
  import { createAboutBookSpreads } from './about-book-content';

  export let musicVideoUrl: string;
  export let pickleballArticleUrl: string;
  export let chessProfileUrl: string;
  export let resumesUrl: string;
  export let portraitUrl: string;
  export let softwareImageUrl: string;
  export let musicImageUrl: string;
  export let pickleballImageUrl: string;

  $: spreads = createAboutBookSpreads({
    musicVideoUrl,
    pickleballArticleUrl,
    chessProfileUrl,
    resumesUrl,
    portraitUrl,
    softwareImageUrl,
    musicImageUrl,
    pickleballImageUrl,
  });
</script>

<section class="about-page-turner" aria-label="About Cyrus Asasi">
  <WebGLBook {spreads} />
</section>
