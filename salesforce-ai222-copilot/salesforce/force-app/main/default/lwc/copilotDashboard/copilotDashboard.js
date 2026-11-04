import { LightningElement, wire } from 'lwc';
import { NavigationMixin } from 'lightning/navigation';
import getDashboard from '@salesforce/apex/CopilotController.getDashboard';

const COLUMNS = [
    { label: 'Opportunité', fieldName: 'name', type: 'text' },
    { label: 'Client', fieldName: 'account', type: 'text' },
    { label: 'Montant', fieldName: 'amount', type: 'currency', cellAttributes: { alignment: 'left' } },
    { label: 'Risque de perte', fieldName: 'lossRiskPct', type: 'percent', typeAttributes: { maximumFractionDigits: 0 } },
    { label: 'Niveau', fieldName: 'risk_level', type: 'text', cellAttributes: { class: { fieldName: 'riskClass' } } },
    { type: 'button', typeAttributes: { label: 'Ouvrir', name: 'open', variant: 'base' } }
];

export default class CopilotDashboard extends NavigationMixin(LightningElement) {
    columns = COLUMNS;
    data;
    error;

    @wire(getDashboard)
    wired({ data, error }) {
        if (data) {
            this.data = JSON.parse(data);
            this.error = undefined;
        } else if (error) {
            this.error = error.body?.message || 'Impossible de charger le tableau de bord.';
        }
    }

    get loading() { return !this.data && !this.error; }
    get conversion() { return this.data ? (this.data.estimated_conversion_rate * 100).toFixed(1) + ' %' : ''; }

    get riskCards() {
        const c = this.data?.risk_counts || {};
        return [
            { key: 'élevé', label: 'Risque élevé', value: c['élevé'] ?? 0, cls: 'risk risk-high' },
            { key: 'moyen', label: 'Risque moyen', value: c['moyen'] ?? 0, cls: 'risk risk-mid' },
            { key: 'faible', label: 'Risque faible', value: c['faible'] ?? 0, cls: 'risk risk-low' }
        ];
    }

    get bars() {
        const d = this.data?.distribution;
        if (!d) return [];
        const max = Math.max(...d.counts, 1);
        return d.bins.map((b, i) => ({
            label: b, count: d.counts[i], style: `height:${Math.round((d.counts[i] / max) * 100)}%`
        }));
    }

    get rows() {
        return (this.data?.top_priority || []).map((r) => ({
            ...r, lossRiskPct: r.loss_risk,
            riskClass: r.risk_level === 'élevé' ? 'slds-text-color_error' : r.risk_level === 'moyen' ? 'slds-text-color_weak' : 'slds-text-color_success'
        }));
    }

    handleRow(e) {
        const id = e.detail.row.id;
        if (/^006[a-zA-Z0-9]{12,15}$/.test(id)) {
            this[NavigationMixin.Navigate]({ type: 'standard__recordPage', attributes: { recordId: id, actionName: 'view' } });
        }
    }
}
