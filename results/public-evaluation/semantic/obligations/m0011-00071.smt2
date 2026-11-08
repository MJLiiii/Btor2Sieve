(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_2 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x917 (and (distinct i_2 (_ bv7 4)) true)))
(not $x917)))
(check-sat)
