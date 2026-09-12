import pandas as pd
import numpy as np

input_file = "/Users/jatinjaglan/Desktop/project 3/online_retail_II.xlsx"
output_file = "/Users/jatinjaglan/Desktop/project 3/Online_Retail_RFM_Tableau_v2.xlsx"

df = pd.read_excel(
    input_file,
    sheet_name="Year 2009-2010"
)

df = df.drop_duplicates().copy()

df["Sales"] = df["Quantity"] * df["Price"]

df["Year"] = df["InvoiceDate"].dt.year
df["Month"] = df["InvoiceDate"].dt.month
df["Month_Name"] = df["InvoiceDate"].dt.month_name()
df["Day_Name"] = df["InvoiceDate"].dt.day_name()
df["Hour"] = df["InvoiceDate"].dt.hour

df["Return_Flag"] = np.where(df["Quantity"] < 0, 1, 0)

rfm_data = df[
    (df["Quantity"] > 0) &
    (df["Price"] > 0) &
    (df["Customer ID"].notna())
].copy()

reference_date = rfm_data["InvoiceDate"].max()

recency = (
    rfm_data.groupby("Customer ID")["InvoiceDate"]
    .max()
    .apply(lambda x: (reference_date - x).days)
)

frequency = (
    rfm_data.groupby("Customer ID")["Invoice"]
    .nunique()
)

total_orders = (
    rfm_data.groupby("Customer ID")["Invoice"]
    .nunique()
)

monetary = (
    rfm_data.groupby("Customer ID")["Sales"]
    .sum()
)

rfm = pd.DataFrame({
    "Recency": recency,
    "Frequency": frequency,
    "Total_Orders": total_orders,
    "Monetary": monetary
})

rfm["R_Score"] = pd.qcut(
    rfm["Recency"],
    q=5,
    labels=[5, 4, 3, 2, 1]
)

rfm["F_Score"] = pd.cut(
    rfm["Frequency"],
    bins=[0, 1, 3, 5, 10, np.inf],
    labels=[1, 2, 3, 4, 5],
    include_lowest=True
)

rfm["M_Score"] = pd.qcut(
    rfm["Monetary"].rank(method="first"),
    q=5,
    labels=[1, 2, 3, 4, 5]
)

rfm["RFM_Score"] = (
    rfm["R_Score"].astype(int).astype(str)
    + rfm["F_Score"].astype(int).astype(str)
    + rfm["M_Score"].astype(int).astype(str)
)

def assign_segment(row):
    R = int(row["R_Score"])
    F = int(row["F_Score"])
    M = int(row["M_Score"])

    if R >= 4 and F >= 4 and M >= 4:
        return "Champions"
    elif F >= 4 and M >= 3:
        return "Loyal Customers"
    elif R >= 4 and F <= 3:
        return "Potential Loyalists"
    elif R <= 2 and (F >= 3 or M >= 3):
        return "At Risk"
    else:
        return "Needs Attention"

rfm["Segment"] = rfm.apply(assign_segment, axis=1)

rfm_final = rfm.reset_index()

returns = df[
    (df["Quantity"] < 0) &
    (df["Customer ID"].notna())
].copy()

return_metrics = (
    returns.groupby("Customer ID")
    .agg(
        Return_Transactions=("Invoice", "count"),
        Return_Quantity=("Quantity", lambda x: abs(x.sum())),
        Return_Value=("Sales", lambda x: abs(x.sum()))
    )
)

rfm_final = rfm_final.merge(
    return_metrics,
    on="Customer ID",
    how="left"
)

rfm_final[
    ["Return_Transactions", "Return_Quantity", "Return_Value"]
] = rfm_final[
    ["Return_Transactions", "Return_Quantity", "Return_Value"]
].fillna(0)

rfm_final["Average_Order_Value"] = (
    rfm_final["Monetary"] /
    rfm_final["Total_Orders"]
)

rfm_final["Has_Return"] = np.where(
    rfm_final["Return_Transactions"] > 0,
    "Yes",
    "No"
)

rfm_final = rfm_final[
    [
        "Customer ID",
        "Recency",
        "Frequency",
        "Total_Orders",
        "Monetary",
        "Average_Order_Value",
        "R_Score",
        "F_Score",
        "M_Score",
        "RFM_Score",
        "Segment",
        "Return_Transactions",
        "Return_Quantity",
        "Return_Value",
        "Has_Return"
    ]
]

segment_summary = (
    rfm_final.groupby("Segment")
    .agg(
        Customers=("Customer ID", "count"),
        Total_Revenue=("Monetary", "sum"),
        Total_Orders=("Total_Orders", "sum"),
        Average_Revenue=("Monetary", "mean"),
        Average_Recency=("Recency", "mean"),
        Average_Frequency=("Frequency", "mean"),
        Average_AOV=("Average_Order_Value", "mean"),
        Return_Value=("Return_Value", "sum")
    )
    .sort_values("Total_Revenue", ascending=False)
)

print("\nRFM CUSTOMER SEGMENTATION")
print("=========================")
print("Final dataset shape:", rfm_final.shape)
print("Unique customers:", rfm_final["Customer ID"].nunique())
print("Total orders:", rfm_final["Total_Orders"].sum())
print("Total revenue:", rfm_final["Monetary"].sum())

print(
    "Overall Average Order Value:",
    rfm_final["Monetary"].sum() /
    rfm_final["Total_Orders"].sum()
)

print("\nCustomer segment distribution:")
print(rfm_final["Segment"].value_counts())

print("\nSegment performance:")
print(segment_summary)

print("\nMissing values:")
print(rfm_final.isnull().sum())

with pd.ExcelWriter(
    output_file,
    engine="openpyxl"
) as writer:

    rfm_final.to_excel(
        writer,
        sheet_name="Customer_RFM",
        index=False
    )

    segment_summary.to_excel(
        writer,
        sheet_name="Segment_Summary",
        index=False
    )

print("\nFILE CREATED SUCCESSFULLY")
print(output_file)