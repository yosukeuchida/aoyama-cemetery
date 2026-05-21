import L from 'leaflet';
import iconUrl from 'leaflet/dist/images/marker-icon.png?url';
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png?url';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png?url';

interface PersonPin {
  slug: string;
  name: string;
  shortDescription: string;
  coords: { lat: number; lng: number };
}

const CEMETERY_CENTER: [number, number] = [35.6688, 139.7185];
const OVERVIEW_ZOOM = 16;
const FOCUS_ZOOM = 18;

delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
});

function escapeHtml(s: string): string {
  return s.replace(
    /[&<>"']/g,
    (c) =>
      ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }[c]!)
  );
}

function initOne(el: HTMLElement): void {
  if (el.dataset.initialized === 'true') return;
  el.dataset.initialized = 'true';

  const mode = el.dataset.mode as 'overview' | 'focus';
  const people: PersonPin[] = JSON.parse(el.dataset.people ?? '[]');

  const map = L.map(el, { scrollWheelZoom: false });

  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);

  if (mode === 'overview') {
    map.setView(CEMETERY_CENTER, OVERVIEW_ZOOM);
    people.forEach((p) => {
      const marker = L.marker([p.coords.lat, p.coords.lng]).addTo(map);
      const html =
        `<strong>${escapeHtml(p.name)}</strong>` +
        `<p style="margin:0.4em 0;">${escapeHtml(p.shortDescription)}</p>` +
        `<a href="/people/${encodeURIComponent(p.slug)}/">詳細を見る →</a>`;
      marker.bindPopup(html);
    });
  } else if (mode === 'focus' && people.length > 0) {
    const p = people[0];
    map.setView([p.coords.lat, p.coords.lng], FOCUS_ZOOM);
    L.marker([p.coords.lat, p.coords.lng]).addTo(map);
  }
}

export function initCemeteryMaps(): void {
  const elements = document.querySelectorAll<HTMLElement>('[data-cemetery-map]');
  elements.forEach(initOne);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initCemeteryMaps);
} else {
  initCemeteryMaps();
}
