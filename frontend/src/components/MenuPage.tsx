import { DRINKS } from '../data/drinks';
import './MenuPage.css';

function ScrollCue({ onClick }: { onClick: () => void }) {
  return (
    <button className="scroll-cue" type="button" onClick={onClick} aria-label="Scroll to ask">
      <span>ask about it</span>
      <svg width="20" height="22" viewBox="0 0 20 22" aria-hidden="true">
        <path className="scroll-cue__arrow" d="M10 1 L10 19 M3 12 L10 19 L17 12" />
      </svg>
    </button>
  );
}

export default function MenuPage({ onScrollToAsk }: { onScrollToAsk: () => void }) {
  return (
    <section className="page menu-page">
      <div className="menu-top">
        <div>
          <h1 className="menu-title hand">
            <span>GOJI</span>
            <span className="accent">&amp; GIN</span>
          </h1>
          <p className="menu-kicker">
            Four drinks built from a Flushing shopping trip — dried goods, roasted tea, and
            whatever the liquor store on Main St had open.
          </p>
        </div>
        <svg className="glass-flute doodle" viewBox="0 0 100 210" aria-hidden="true">
          <path d="M30 8 L70 8 L60 95 Q60 118 50 118 Q40 118 40 95 Z" />
          <path d="M50 118 L50 185" />
          <path d="M22 200 Q50 190 78 200" />
          <path
            className="doodle-fill doodle-fill--osmanthus"
            d="M33 14 L67 14 L61 60 Q55 68 50 68 Q45 68 39 60 Z"
          />
        </svg>
      </div>

      <div className="menu-list">
        {DRINKS.map((drink, idx) => (
          <div className="menu-row" key={drink.id}>
            <span className="menu-mark script">{String(idx + 1).padStart(2, '0')}</span>
            <div className="menu-name-wrap">
              <span className="menu-name hand">{drink.name}</span>
              <span className="menu-note">{drink.note}</span>
            </div>
            <span className="menu-tag script">{drink.tagline}</span>
          </div>
        ))}
      </div>

      <div className="menu-footer">
        <p className="provenance">
          <strong>Sourced from</strong> Kar Wor Tong for the dried goods, Ten Ren for tea (cash
          only), Jmart for texture and ice, and a liquor store off Main St for everything with
          proof.
        </p>
        <ScrollCue onClick={onScrollToAsk} />
      </div>

      <svg className="martini-corner doodle" viewBox="0 0 160 150" aria-hidden="true">
        <path d="M10 12 L150 12 L82 78 L82 132" />
        <path d="M52 142 L112 142" />
        <path className="doodle-fill doodle-fill--olive" d="M20 20 L140 20 L82 66 Z" />
        <circle className="doodle-fill doodle-fill--goji" cx="112" cy="18" r="9" />
      </svg>
    </section>
  );
}
