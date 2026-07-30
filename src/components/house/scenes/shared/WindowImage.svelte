<script lang="ts">
  import { withBase } from '@/lib/paths';

  export let src: string;
  export let width: number;
  export let height: number;

  $: imageHref = withBase(src);
</script>

<image
  class="house-window__image"
  href={imageHref}
  x="0"
  y="0"
  {width}
  {height}
  preserveAspectRatio="xMidYMid slice"
  aria-hidden="true"
/>
