<script lang="ts">
  export let boardLabel = 'Next train';
  export let boardPrimary = '00:06';
  export let boardSecondary = 'TO HOME STATION';
</script>

<div class="railway-arrival-board" aria-hidden="true">
  <div class="railway-arrival-board__shell">
    <div class="railway-arrival-board__label">{boardLabel}</div>
    <div class="railway-arrival-board__primary">{boardPrimary}</div>
    <div class="railway-arrival-board__secondary">{boardSecondary}</div>
  </div>
</div>

<style>
  .railway-arrival-board {
    display: grid;
    pointer-events: none;
  }

  .railway-arrival-board__shell {
    position: relative;
    display: grid;
    min-width: 13.4rem;
    gap: 0.18rem;
    padding: 0.58rem 0.72rem 0.62rem;
    border: 1px solid #40332a;
    border-radius: 0.18rem;
    background:
      linear-gradient(180deg, #16110e 0%, #090705 100%),
      repeating-linear-gradient(0deg, rgb(255 255 255 / 0.03) 0 1px, transparent 1px 3px);
    box-shadow:
      0 0 0 1px rgb(255 255 255 / 0.03) inset,
      0 0.55rem 1rem rgb(0 0 0 / 0.18);
  }

  .railway-arrival-board__shell::before {
    position: absolute;
    inset: 0.34rem;
    border: 1px solid rgb(255 145 36 / 0.16);
    border-radius: 0.08rem;
    content: '';
  }

  .railway-arrival-board__label,
  .railway-arrival-board__secondary {
    position: relative;
    z-index: 1;
    overflow: hidden;
    color: #d98d42;
    font-family: var(--font-mono);
    font-size: 0.44rem;
    letter-spacing: 0.14em;
    text-overflow: ellipsis;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .railway-arrival-board__primary {
    position: relative;
    z-index: 1;
    overflow: hidden;
    color: #ff941e;
    font-family: var(--font-mono);
    font-size: 1.06rem;
    font-variant-numeric: tabular-nums;
    font-weight: 700;
    letter-spacing: 0.12em;
    line-height: 1;
    text-overflow: ellipsis;
    text-shadow:
      0 0 0.16rem rgb(255 128 0 / 1),
      0 0 0.72rem rgb(255 128 0 / 0.45),
      0 0 1.1rem rgb(255 128 0 / 0.18);
    white-space: nowrap;
  }

  @media (max-width: 48rem) {
    .railway-arrival-board__secondary {
      display: none;
    }

    .railway-arrival-board__shell {
      min-width: 8.6rem;
      padding: 0.4rem 0.46rem 0.44rem;
    }

    .railway-arrival-board__label {
      font-size: 0.36rem;
    }

    .railway-arrival-board__primary {
      font-size: 0.84rem;
      letter-spacing: 0.08em;
    }
  }
</style>
