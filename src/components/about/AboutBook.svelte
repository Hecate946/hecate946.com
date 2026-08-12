<script lang="ts">
  import WebGLBook from './WebGLBook.svelte';
  import { createAboutBookSpreads } from './about-book-content';

  export let musicVideoUrl: string;
  export let pickleballArticleUrl: string;
  export let chessProfileUrl: string;
  export let resumesUrl: string;
  export let portraitUrl: string;

  $: spreads = createAboutBookSpreads({
    musicVideoUrl,
    pickleballArticleUrl,
    chessProfileUrl,
    resumesUrl,
    portraitUrl,
  });
</script>

<section class="about-page-turner" aria-label="About Cyrus Asasi">
  <WebGLBook {spreads} />
</section>
