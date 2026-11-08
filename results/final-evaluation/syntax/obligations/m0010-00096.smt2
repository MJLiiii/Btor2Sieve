(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x2623 (and (distinct i_6 (_ bv1 8)) true)))
(not $x2623)))
(check-sat)
