<div class="railway-track" aria-hidden="true">
  <div class="railway-ballast"></div>
  <div class="railway-ballast-highlight"></div>
  <div class="railway-sleepers"></div>
  <div class="railway-rail railway-rail--far"></div>
  <div class="railway-rail railway-rail--near"></div>
</div>

<style>
  .railway-track {
    position: absolute;
    z-index: 8;
    right: -2%;
    bottom: 0;
    left: -2%;
    height: 6.1rem;
    pointer-events: none;
  }

  .railway-ballast {
    position: absolute;
    inset: auto 0 0;
    height: 4.75rem;
    background:
      radial-gradient(ellipse at 10% 34%, rgb(73 73 73 / 0.55) 0 0.22rem, transparent 0.24rem),
      radial-gradient(ellipse at 18% 72%, rgb(24 24 24 / 0.9) 0 0.24rem, transparent 0.27rem),
      radial-gradient(ellipse at 31% 48%, rgb(87 87 87 / 0.45) 0 0.16rem, transparent 0.19rem),
      radial-gradient(ellipse at 46% 68%, rgb(33 33 33 / 0.88) 0 0.22rem, transparent 0.25rem),
      radial-gradient(ellipse at 63% 32%, rgb(88 88 88 / 0.4) 0 0.18rem, transparent 0.2rem),
      radial-gradient(ellipse at 76% 58%, rgb(18 18 18 / 0.92) 0 0.25rem, transparent 0.28rem),
      radial-gradient(ellipse at 92% 38%, rgb(79 79 79 / 0.4) 0 0.17rem, transparent 0.19rem),
      linear-gradient(180deg, #202020 0%, #171717 32%, #111 66%, #090909 100%);
    background-size:
      4rem 3.1rem,
      4.8rem 3.8rem,
      3.6rem 2.8rem,
      4.4rem 3.4rem,
      4rem 3rem,
      5.1rem 3.7rem,
      3.9rem 2.9rem,
      auto;
    border-top: 1px solid rgb(255 255 255 / 0.045);
    box-shadow:
      inset 0 0.14rem 0 rgb(255 255 255 / 0.05),
      0 -0.8rem 1.25rem rgb(0 0 0 / 0.22);
  }

  .railway-ballast-highlight {
    position: absolute;
    right: 0;
    bottom: 3.05rem;
    left: 0;
    height: 0.35rem;
    background: linear-gradient(180deg, rgb(255 255 255 / 0.06), transparent);
    opacity: 0.6;
  }

  .railway-sleepers {
    position: absolute;
    right: 0;
    bottom: 1.08rem;
    left: 0;
    height: 2.55rem;
    background:
      repeating-linear-gradient(
        90deg,
        transparent 0 0.8rem,
        #120b08 0.8rem 1.02rem,
        #5a3620 1.02rem 1.98rem,
        #2b170f 1.98rem 2.28rem,
        transparent 2.28rem 3.82rem
      );
    filter: drop-shadow(0 0.24rem 0.18rem rgb(0 0 0 / 0.55));
    opacity: 0.96;
  }

  .railway-rail {
    position: absolute;
    right: 0;
    left: 0;
    height: 0.86rem;
    border-radius: 999px;
    background:
      linear-gradient(180deg, rgb(255 255 255 / 0.22) 0 10%, transparent 10% 18%),
      linear-gradient(180deg, #555 0%, #2a2a2a 36%, #141414 68%, #060606 100%);
    box-shadow:
      0 0.26rem 0.22rem rgb(0 0 0 / 0.42),
      inset 0 0.09rem 0 rgb(255 255 255 / 0.16),
      inset 0 -0.08rem 0 rgb(0 0 0 / 0.42);
  }

  .railway-rail::before,
  .railway-rail::after {
    position: absolute;
    left: 0;
    right: 0;
    content: '';
  }

  .railway-rail::before {
    top: 0.08rem;
    height: 0.18rem;
    border-radius: 999px;
    background: linear-gradient(180deg, rgb(255 255 255 / 0.36), rgb(255 255 255 / 0.06));
  }

  .railway-rail::after {
    bottom: -0.24rem;
    height: 0.28rem;
    border-radius: 0 0 0.5rem 0.5rem;
    background: linear-gradient(180deg, #222, #0a0a0a);
    opacity: 0.9;
  }

  .railway-rail--far {
    bottom: 3.34rem;
  }

  .railway-rail--near {
    bottom: 1.56rem;
  }

  @media (max-width: 48rem) {
    .railway-track {
      height: 5.2rem;
    }

    .railway-ballast {
      height: 4.05rem;
    }

    .railway-ballast-highlight {
      bottom: 2.55rem;
    }

    .railway-sleepers {
      bottom: 0.98rem;
      height: 2rem;
      background: repeating-linear-gradient(
        90deg,
        transparent 0 0.62rem,
        #120b08 0.62rem 0.82rem,
        #5a3620 0.82rem 1.46rem,
        #2b170f 1.46rem 1.7rem,
        transparent 1.7rem 2.9rem
      );
    }

    .railway-rail {
      height: 0.74rem;
    }

    .railway-rail--far {
      bottom: 2.84rem;
    }

    .railway-rail--near {
      bottom: 1.3rem;
    }
  }
</style>
