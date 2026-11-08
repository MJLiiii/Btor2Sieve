(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_4 () (_ BitVec 3))
(assert
 true)
(assert
 (let (($x34 (and (distinct i_4 (_ bv7 3)) true)))
(not $x34)))
(check-sat)
