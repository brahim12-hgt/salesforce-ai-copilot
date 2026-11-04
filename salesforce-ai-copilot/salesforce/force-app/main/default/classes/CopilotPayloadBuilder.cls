/**
 * Construit la charge utile depuis Salesforce, au schéma des features du modèle (dataset CRM Sales Opportunities).
 * Requêtes en USER_MODE : l'IA ne reçoit que les données visibles par l'utilisateur.
 * Les champs absents sont complétés côté backend (référentiels ou médianes d'entraînement).
 */
public with sharing class CopilotPayloadBuilder {

    public static Map<String, Object> build(Id oppId) {
        Opportunity o = [
            SELECT Id, Name, Amount, CreatedDate,
                   Account.Name, Account.Industry, Account.AnnualRevenue, Account.NumberOfEmployees,
                   Account.YearStarted, Account.BillingCountry, Account.ParentId,
                   Owner.Name, Owner.Manager.Name
            FROM Opportunity WHERE Id = :oppId WITH USER_MODE LIMIT 1
        ];
        List<OpportunityLineItem> items = [
            SELECT Product2.Name, Product2.Family FROM OpportunityLineItem
            WHERE OpportunityId = :oppId WITH USER_MODE LIMIT 1
        ];
        Map<String, Object> f = new Map<String, Object>{
            'opportunity_id' => String.valueOf(o.Id),
            'name' => o.Name,
            'account' => o.Account?.Name,
            'account_name' => o.Account?.Name,
            'sector' => o.Account?.Industry,
            'revenue' => o.Account?.AnnualRevenue == null ? null : o.Account.AnnualRevenue / 1000000,
            'employees' => o.Account?.NumberOfEmployees,
            'office_location' => o.Account?.BillingCountry,
            'is_subsidiary' => o.Account?.ParentId == null ? 0 : 1,
            'sales_agent' => o.Owner.Name,
            'manager' => o.Owner.Manager?.Name,
            'sales_price' => o.Amount,
            'engage_month' => o.CreatedDate.month()
        };
        String yearStarted = o.Account?.YearStarted;
        if (yearStarted != null && yearStarted.isNumeric() && yearStarted.length() == 4) {
            f.put('company_age', Date.today().year() - Integer.valueOf(yearStarted));
        }
        if (!items.isEmpty()) {
            f.put('product', items[0].Product2.Name);
            f.put('series', items[0].Product2.Family);
        }
        return f;
    }

    public static List<Map<String, Object>> interactions(Id oppId) {
        List<Map<String, Object>> out = new List<Map<String, Object>>();
        for (Task t : [
            SELECT Id, Subject, Description, ActivityDate, TaskSubtype FROM Task
            WHERE WhatId = :oppId WITH USER_MODE ORDER BY CreatedDate DESC LIMIT 20
        ]) {
            String type = t.TaskSubtype == 'Call' ? 'call' : (t.TaskSubtype == 'Email' ? 'email' : 'note');
            out.add(new Map<String, Object>{
                'id' => String.valueOf(t.Id), 'type' => type,
                'date' => String.valueOf(t.ActivityDate),
                'text' => ((t.Subject == null ? '' : t.Subject) + '. ' + (t.Description == null ? '' : t.Description)).abbreviate(2000)
            });
        }
        return out;
    }
}
