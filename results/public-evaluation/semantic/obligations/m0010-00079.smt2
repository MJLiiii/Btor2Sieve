(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x2283 (and (distinct i_4 (_ bv1 32)) true)))
(not $x2283)))
(check-sat)
