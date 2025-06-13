import streamlit as st
import pandas as pd
import math
st.set_page_config(page_title="SU-Lånberegner", page_icon="📊") 
st.title("📊 SU-Lånberegner")

st.write("### Indtast data")
col1, col2 = st.columns(2)
su_loan_amount = col1.number_input("SU Lånebeløb (kr.)", min_value=0, value=100000)
deposit = col1.number_input("Ekstraordinært afdrag", min_value=0, value=0)
interest_rate = col2.number_input("Renten (i %)", min_value=0.0, value=3.75)
loan_term = col2.number_input("Tilbagebetalingsperiode (i år)", min_value=0, max_value=15, value=10)

# --- Calculations ---
loan_amount = su_loan_amount - deposit

# Initialize df as an empty DataFrame with correct columns
df_schedule = pd.DataFrame(columns=["Måned", "Betaling", "Afdrag", "Rente", "Restgæld", "År"])

if loan_amount <= 0:
    st.write("### Tilbagebetaling")
    st.info("Lånebeløb (efter evt. ekstraordinært afdrag) er 0 kr. eller mindre. Ingen beregning nødvendig.")
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric(label="Månedlig betaling", value="0.00 kr.")
    m_col2.metric(label="Samlede betalinger", value="0 kr.")
    m_col3.metric(label="Samlede renter", value="0 kr.")
    
    st.write("### Rentefradragsberegning")
    st.write("Intet lån, intet rentefradrag.")
    
    st.write("### Betalingsplan (Amortiseringsoversigt)")
    st.write("Intet lån, ingen betalingsplan.")

elif loan_term == 0: # Loan exists, but term is 0 years (immediate repayment)
    st.write("### Tilbagebetaling")
    st.info("Lånet tilbagebetales med det samme (0 års løbetid).")
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric(label="Engangsbetaling", value=f"{loan_amount:,.2f} kr.")
    m_col2.metric(label="Samlede betalinger", value=f"{loan_amount:,.0f} kr.")
    m_col3.metric(label="Samlede renter", value="0 kr.")

    schedule_data = [[1, loan_amount, loan_amount, 0.0, 0.0, 1]]
    df_schedule = pd.DataFrame(schedule_data, columns=["Måned", "Betaling", "Afdrag", "Rente", "Restgæld", "År"])
    
    st.write("### Rentefradragsberegning")
    st.write("Lånet tilbagebetales med det samme, så der er ingen renter at fradrage.")
    
    st.write("### Betalingsplan (Amortiseringsoversigt)")
    st.write("#### Detaljeret Månedlig Oversigt")
    st.dataframe(df_schedule.style.format({
        "Betaling": "{:,.2f} kr.", "Afdrag": "{:,.2f} kr.",
        "Rente": "{:,.2f} kr.", "Restgæld": "{:,.2f} kr."
    }))
    st.write("#### Restgældsudvikling over Tid")
    st.write("Lånet er fuldt tilbagebetalt med det samme.")

else: # loan_amount > 0 and loan_term > 0
    monthly_interest_rate = (interest_rate / 100) / 12
    number_of_payments = loan_term * 12 # This will be a float if loan_term is float
    num_payments_int = int(round(number_of_payments)) # Use rounded int for iterations

    if num_payments_int == 0: # Should not happen if loan_term > 0, but safeguard
        monthly_payment = loan_amount
    elif monthly_interest_rate == 0: # No interest
        monthly_payment = loan_amount / num_payments_int if num_payments_int > 0 else 0
    else: # Standard amortization formula with interest
        try:
            # Ensure number_of_payments in formula is the precise one, not rounded, if it matters
            # For simplicity, using num_payments_int as it's standard for fixed N payments
            denominator = ((1 + monthly_interest_rate) ** num_payments_int - 1)
            if denominator == 0: # Avoid division by zero
                monthly_payment = loan_amount / num_payments_int if num_payments_int > 0 else 0 # Effectively 0 interest
            else:
                monthly_payment = (
                    loan_amount
                    * (monthly_interest_rate * (1 + monthly_interest_rate) ** num_payments_int)
                    / denominator
                )
            if monthly_payment < 0 or not math.isfinite(monthly_payment):
                raise ValueError("Calculated monthly payment is invalid.")
        except (OverflowError, ValueError, ZeroDivisionError):
            st.error("Der opstod en fejl ved beregning af månedlig ydelse. Kontroller inputværdier (f.eks. meget lav rente og lang løbetid kan give problemer).")
            monthly_payment = 0 # Fallback

    total_payments_estimate = monthly_payment * num_payments_int
    total_interest_estimate = total_payments_estimate - loan_amount
    if total_interest_estimate < -0.01 : total_interest_estimate = 0 # Cap at 0

    st.write("### Tilbagebetaling")
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric(label="Månedlig betaling (ca.)", value=f"{monthly_payment:,.2f} kr.")
    m_col2.metric(label="Samlede betalinger (ca.)", value=f"{total_payments_estimate:,.0f} kr.")
    m_col3.metric(label="Samlede renter (ca.)", value=f"{total_interest_estimate:,.0f} kr.")

    # Create a data-frame with the payment schedule.
    schedule = []
    remaining_balance = loan_amount
    
    if num_payments_int > 0 and monthly_payment > 0.005: # Proceed only if there are payments to schedule
        for i in range(1, num_payments_int + 1):
            interest_this_month = remaining_balance * monthly_interest_rate
            if interest_this_month < 0: interest_this_month = 0 # Safety for float issues

            if i == num_payments_int: # Last payment, adjust to clear balance
                principal_this_month = remaining_balance
                payment_this_month = principal_this_month + interest_this_month
            else:
                principal_this_month = monthly_payment - interest_this_month
                payment_this_month = monthly_payment
            
            # Ensure principal payment is not negative or grossly overshooting
            if principal_this_month < 0 and i != num_payments_int : principal_this_month = 0 # Avoid negative principal
            if principal_this_month > remaining_balance + 0.01 and i != num_payments_int: # Cap if overshooting
                principal_this_month = remaining_balance

            remaining_balance -= principal_this_month
            if abs(remaining_balance) < 0.01: # Threshold for float precision, effectively zero
                remaining_balance = 0.0
            
            year = math.ceil(i / 12)
            schedule.append(
                [i, payment_this_month, principal_this_month, interest_this_month, remaining_balance, year]
            )
        df_schedule = pd.DataFrame(schedule, columns=["Måned", "Betaling", "Afdrag", "Rente", "Restgæld", "År"])

    # Interest Deduction Calculation (Accurate version)
    st.write("### Rentefradragsberegning (Baseret på Afdragsplan)")
    if not df_schedule.empty and "Rente" in df_schedule.columns and df_schedule["Rente"].sum() > 0.005:
        annual_interest_summary = df_schedule.groupby("År")["Rente"].sum().reset_index()
        # Filter out years with negligible interest if any (e.g. if loan ends early in a year)
        annual_interest_summary = annual_interest_summary[annual_interest_summary["Rente"] > 0.005] 
        
        if not annual_interest_summary.empty:
            annual_interest_summary.rename(columns={"Rente": "Samlede Renter Betalt i Året"}, inplace=True)
            tax_deduction_rate = 0.331  # 33,1 %
            annual_interest_summary["Rentefradrag (Årligt)"] = annual_interest_summary["Samlede Renter Betalt i Året"] * tax_deduction_rate
            
            st.write("Nedenfor ses de faktiske årlige renteudgifter og det tilsvarende skattefradrag:")
            st.dataframe(annual_interest_summary.style.format({
                "Samlede Renter Betalt i Året": "{:,.2f} kr.",
                "Rentefradrag (Årligt)": "{:,.2f} kr."
            }))
            
            total_interest_paid_schedule = annual_interest_summary["Samlede Renter Betalt i Året"].sum()
            total_deduction_schedule = annual_interest_summary["Rentefradrag (Årligt)"].sum()

            st.write(f"Over hele lånets løbetid betaler du i alt **{total_interest_paid_schedule:,.2f} kr.** i renter ifølge planen.")
            st.write(f"Det samlede rentefradrag over lånets løbetid vil være **{total_deduction_schedule:,.2f} kr.**")
        else:
            st.write("Ingen væsentlige renteudgifter at beregne fradrag for (f.eks. ved 0% rente eller meget kort løbetid).")
    else:
        st.write("Ingen renteudgifter at beregne fradrag for (f.eks. ved 0% rente, intet lån, eller ingen gyldig afdragsplan).")

    # Display the data-frame and chart.
    st.write("### Betalingsplan (Amortiseringsoversigt)")
    st.write("#### Detaljeret Månedlig Oversigt")
    if not df_schedule.empty:
        st.dataframe(df_schedule.style.format({
            "Betaling": "{:,.2f} kr.", "Afdrag": "{:,.2f} kr.",
            "Rente": "{:,.2f} kr.", "Restgæld": "{:,.2f} kr."
        }))
    else:
        st.write("Ingen betalingsplan at vise (muligvis pga. ugyldige input eller 0 månedlig betaling).")

    st.write("#### Restgældsudvikling over Tid")
    if not df_schedule.empty and "År" in df_schedule.columns and "Restgæld" in df_schedule.columns:
        chart_data = df_schedule.groupby("År")["Restgæld"].min().reset_index()
        # Add starting point for the graph (Year 0, initial loan amount)
        if loan_amount > 0 :
            start_point = pd.DataFrame([{"År": 0, "Restgæld": loan_amount}])
            chart_data = pd.concat([start_point, chart_data], ignore_index=True).sort_values(by="År")
        
        st.line_chart(chart_data.set_index("År"))
    else:
        st.write("Ingen data at vise i grafen.")