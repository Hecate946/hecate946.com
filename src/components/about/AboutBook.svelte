<script lang="ts">
  import PaperStack from './PaperStack.svelte';
  import { createAboutPaperPages } from './about-book-content';

  export let portraitUrl: string;

  $: pages = createAboutPaperPages({
    portraitUrl,
  });
</script>

<section class="about-page-turner" aria-label="About Cyrus Asasi">
  <PaperStack {pages} />
</section>
