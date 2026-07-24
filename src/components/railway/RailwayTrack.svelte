<div class="railway-track" aria-hidden="true">
  <div class="railway-ballast"></div>
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
    height: 5.8rem;
    pointer-events: none;
  }

  .railway-ballast {
    position: absolute;
    inset: auto 0 0;
    height: 4.45rem;
    border-top: 1px solid rgb(255 255 255 / 0.05);
    background:
      radial-gradient(ellipse at 9% 25%, #262626 0 0.16rem, transparent 0.18rem),
      radial-gradient(ellipse at 24% 68%, #050505 0 0.2rem, transparent 0.22rem),
      radial-gradient(ellipse at 48% 36%, #2b2b2b 0 0.15rem, transparent 0.18rem),
      radial-gradient(ellipse at 76% 62%, #080808 0 0.19rem, transparent 0.22rem),
      radial-gradient(ellipse at 91% 28%, #292929 0 0.14rem, transparent 0.17rem),
      linear-gradient(180deg, #181818 0%, #111 42%, #080808 100%);
    background-size:
      3.2rem 2.6rem,
      4.6rem 3.3rem,
      3.8rem 3rem,
      4.2rem 3.5rem,
      3.4rem 2.8rem,
      auto;
    box-shadow:
      inset 0 0.1rem 0 rgb(255 255 255 / 0.06),
      0 -0.55rem 1rem rgb(0 0 0 / 0.2);
  }

  .railway-sleepers {
    position: absolute;
    right: 0;
    bottom: 1.02rem;
    left: 0;
    height: 2.35rem;
    background: repeating-linear-gradient(
      90deg,
      transparent 0 0.9rem,
      #140d09 0.9rem 1.2rem,
      #422718 1.2rem 1.95rem,
      #20120c 1.95rem 2.28rem,
      transparent 2.28rem 4rem
    );
    filter: drop-shadow(0 0.2rem 0.16rem rgb(0 0 0 / 0.55));
  }

  .railway-rail {
    position: absolute;
    right: 0;
    left: 0;
    height: 0.72rem;
    border-radius: 999px;
    border-top: 0.06rem solid rgb(255 255 255 / 0.14);
    background: linear-gradient(180deg, #272727 0%, #101010 52%, #020202 100%);
    box-shadow:
      0 0.24rem 0.2rem rgb(0 0 0 / 0.42),
      inset 0 0.08rem 0 rgb(255 255 255 / 0.08);
  }

  .railway-rail--far {
    bottom: 3.12rem;
  }

  .railway-rail--near {
    bottom: 1.46rem;
  }

  @media (max-width: 48rem) {
    .railway-track {
      height: 5rem;
    }

    .railway-ballast {
      height: 3.8rem;
    }

    .railway-sleepers {
      bottom: 0.9rem;
      height: 1.85rem;
      background: repeating-linear-gradient(
        90deg,
        transparent 0 0.65rem,
        #140d09 0.65rem 0.9rem,
        #422718 0.9rem 1.4rem,
        #20120c 1.4rem 1.65rem,
        transparent 1.65rem 3rem
      );
    }

    .railway-rail--far {
      bottom: 2.65rem;
    }

    .railway-rail--near {
      bottom: 1.25rem;
    }
  }
</style>
