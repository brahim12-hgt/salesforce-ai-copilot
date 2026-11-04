import { LightningElement, api } from 'lwc';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';
import { notifyRecordUpdateAvailable } from 'lightning/uiRecordApi';
import getInsights from '@salesforce/apex/CopilotController.getInsights';
import recordDecision from '@salesforce/apex/CopilotController.recordDecision';

export default class OpportunityInsights extends LightningElement {
    @api recordId;
    result;
    loading = false;
    error;
    editingId;
    editText = '';
    decided = {};

    connectedCallback() { this.refresh(); }

    async refresh() {
        this.loading = true;
        this.error = undefined;
        try {
            this.result = JSON.parse(await getInsights({ recordId: this.recordId }));
            this.decided = {};
            await notifyRecordUpdateAvailable([{ recordId: this.recordId }]);
        } catch (e) {
            this.error = e.body?.message || "L'analyse a échoué. Réessayez dans un instant.";
        } finally {
            this.loading = false;
        }
    }

    get hasResult() { return !!this.result; }
    get pred() { return this.result?.prediction; }
    get riskPct() { return Math.round(this.pred.loss_risk * 100); }
    get gaugeStyle() { return `width:${this.riskPct}%`; }
    get gaugeClass() { return 'gauge-fill ' + (this.pred.risk_level === 'élevé' ? 'high' : this.pred.risk_level === 'moyen' ? 'mid' : 'low'); }
    get summary() { return this.result?.summary; }
    get hasObjections() { return this.summary?.objections?.length > 0; }
    get hasNeeds() { return this.summary?.needs?.length > 0; }
    get hasCommitments() { return this.summary?.commitments?.length > 0; }
    get sourcesText() { return (this.summary?.sources || []).join(', '); }

    get factors() {
        const max = Math.max(...this.pred.factors.map((f) => Math.abs(f.impact)), 0.0001);
        return this.pred.factors.map((f) => ({
            ...f, key: f.feature,
            barStyle: `width:${Math.round((Math.abs(f.impact) / max) * 100)}%`,
            barClass: 'f-bar ' + (f.direction === 'augmente_risque' ? 'up' : 'down'),
            hint: f.direction === 'augmente_risque' ? 'Augmente le risque' : 'Réduit le risque'
        }));
    }

    get recommendations() {
        return (this.result?.recommendations || []).map((r) => ({
            ...r,
            isEditing: this.editingId === r.id,
            status: this.decided[r.id],
            pending: !this.decided[r.id],
            badge: 'slds-badge ' + (r.priority === 'haute' ? 'badge-high' : '')
        }));
    }

    startEdit(e) {
        this.editingId = e.target.dataset.id;
        this.editText = this.result.recommendations.find((r) => r.id === this.editingId).action;
    }
    handleEditText(e) { this.editText = e.target.value; }
    cancelEdit() { this.editingId = undefined; }
    accept(e) { this.decide(e.target.dataset.id, 'acceptée'); }
    reject(e) { this.decide(e.target.dataset.id, 'rejetée'); }
    saveEdit() { this.decide(this.editingId, 'modifiée', this.editText); }

    async decide(id, decision, modifiedAction) {
        const r = this.result.recommendations.find((x) => x.id === id);
        try {
            await recordDecision({
                oppId: this.recordId, recId: id, action: r.action, justification: r.justification,
                priority: r.priority, decision, modifiedAction: modifiedAction || null
            });
            this.decided = { ...this.decided, [id]: decision };
            this.editingId = undefined;
            this.dispatchEvent(new ShowToastEvent({ title: 'Décision enregistrée', message: `Recommandation ${decision}.`, variant: 'success' }));
        } catch (e) {
            this.dispatchEvent(new ShowToastEvent({ title: 'Enregistrement impossible', message: e.body?.message || 'Réessayez.', variant: 'error' }));
        }
    }
}
