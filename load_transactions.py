from save_transaction import transactions


def load_transaction(transaction_id):
    """Loads the transaction with the given ID"""
    return transactions[transaction_id]


def load_transactions_for_user(user_id):
    """Loads the transactions which were sent by the given user"""
    user_transactions = [t for t in transactions.values() if t.sender_id == user_id]
    return user_transactions
