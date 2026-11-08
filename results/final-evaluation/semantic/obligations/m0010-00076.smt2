(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x5401 (and (distinct i_4 (_ bv1 32)) true)))
(not $x5401)))
(check-sat)
