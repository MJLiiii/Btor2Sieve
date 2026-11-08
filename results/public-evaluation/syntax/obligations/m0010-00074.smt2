(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 32))
(assert
 true)
(assert
 (let (($x1369 (and (distinct i_4 (_ bv0 32)) true)))
(not $x1369)))
(check-sat)
